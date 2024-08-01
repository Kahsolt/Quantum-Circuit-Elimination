#!/usr/bin/env python3
# Author: Armit
# Create Time: 2024/07/08 

from __future__ import annotations

import random
from fractions import Fraction
from copy import deepcopy
from dataclasses import dataclass, field
from typing import List, Optional, NamedTuple

import numpy as np
from numpy import pi as PI
from app.sdata import GameConst

PI2 = PI * 2
PI4 = PI * 4
PI_2 = PI / 2
PI_4 = PI / 4
D_GATE = ['CZ', 'CNOT', 'SWAP']
P_GATE = ['RX', 'RY', 'RZ']


@dataclass
class XGate:
  name: str
  param: Optional[float] = None

  def __repr__(self):
    s = f'{self.name}'
    if self.param:
      frac = Fraction(round(self.param / PI, 2))
      a, b = frac.as_integer_ratio()
      if abs(a) == abs(b) == 1:
        s += f'(-π)' if self.param < 0 else f'(π)'
      else:
        s += f'({a}/{b}π)'
    return s

  def clone(self) -> IGate:
    return deepcopy(self)

  def json(self):
    return [self.name, self.param]


@dataclass
class IGate:
  name: str
  target_qubit: int = None
  param: Optional[float] = None
  control_qubit: Optional[int] = None

  def __repr__(self):
    s = f'{self.name}'
    s += f'(q{self.target_qubit}'
    if self.control_qubit is not None:
      s += f', q{self.control_qubit}'
    if self.param:
      frac = Fraction(round(self.param / PI, 2))
      a, b = frac.as_integer_ratio()
      if abs(a) == abs(b) == 1:
        s += f', -π' if self.param < 0 else f', π'
      else:
        s += f', {a}/{b}π'
    s += ')'
    return s

  def clone(self) -> IGate:
    return deepcopy(self)

  def json(self):
    return [self.name, self.param, self.target_qubit, self.control_qubit]


@dataclass
class ICircuit:
  n_qubit: int
  gates: List[IGate] = field(default_factory=list)

  def __len__(self) -> int:
    return len(self.gates)

  def __getitem__(self, idx:int) -> IGate:
    return self.gates[idx]

  def append(self, g:IGate):
    self.gates.append(g)

  def remove(self, idx:int):
    self.gates.pop(idx)

  def clone(self) -> ICircuit:
    return deepcopy(self)

  def json(self):
    return [g.json() for g in self.gates]


def rand_xgate() -> XGate:
  name = np.random.choice(GameConst.gate_pool_names, p=GameConst.gate_pool_probs)
  param = (random.choice(GameConst.rand_gate_rot) / 4 * PI) if name in P_GATE else None
  return XGate(name, param)


def get_circuit_depth(circuit:ICircuit, n_qubit:int) -> List[int]:
  depth = [0] * n_qubit
  for gate in circuit:
    if gate.control_qubit is None:
      u = gate.target_qubit
      depth[u] += 1
    else:
      u = gate.target_qubit
      v = gate.control_qubit
      maxD = max(depth[u], depth[v])
      depth[u] = depth[v] = maxD + 1
  return depth


def check_gate_can_put(circuit:ICircuit, gate:IGate, n_qubit:int, max_depth:int) -> bool:
  depth = get_circuit_depth(circuit, n_qubit)
  if gate.control_qubit is not None:
    D = max(depth[gate.target_qubit], depth[gate.control_qubit]) + 1
  else:
    D = depth[gate.target_qubit] + 1
  return D <= max_depth


def check_circuit_is_full(circuit:ICircuit, gates:List[IGate], n_qubit:int, max_depth:int) -> bool:
  depth = get_circuit_depth(circuit, n_qubit)
  has_single = False
  for gate in gates:
    if gate.name not in D_GATE:
      has_single = True
      break
  return sum([max_depth - d for d in depth]) < (1 if has_single else 2)


class SettleResult(NamedTuple):
  circuit: ICircuit
  score: int = 0
  n_fuse: int = 0
  n_elim: int = 0


@dataclass
class LGate:
  depth: int
  gate: IGate

def cvt_rots(g:IGate) -> IGate:
  if g.name in ['X', 'Y', 'Z']: return IGate(f'R{g.name}', g.target_qubit, PI)
  if g.name == 'T' : return IGate('RZ', g.target_qubit, +PI_2)
  if g.name == 'TD': return IGate('RZ', g.target_qubit, -PI_2)
  if g.name == 'S' : return IGate('RZ', g.target_qubit, +PI_4)
  if g.name == 'SD': return IGate('RZ', g.target_qubit, -PI_4)
  return g

def is_dagger(A:IGate, B:IGate):
  A = cvt_rots(A) 
  B = cvt_rots(B) 

  name_match = A.name == B.name
  name_set = {A.name, B.name}
  target_match = A.target_qubit == B.target_qubit
  control_match = A.control_qubit == B.control_qubit
  if A.name in ('H', 'X', 'Y', 'Z') and name_match:
    return target_match
  elif A.name in ('CNOT', 'CZ') and name_match:
    return target_match and control_match
  elif A.name in ('T', 'TD'):
    return name_set == {'T', 'TD'} and target_match
  elif A.name in ('S', 'SD'):
    return name_set == {'S', 'SD'} and target_match
  elif A.name in ['RX', 'RY', 'RZ'] and name_match:
    param = (A.param + B.param) % PI2
    #if param - PI > 1e-5: param = PI2 - param
    return target_match and abs(param) < 1e-5

def merge_rot_if_possible(A:IGate, B:IGate) -> IGate:
  A = cvt_rots(A) 
  B = cvt_rots(B) 

  if A.name != B.name: return
  if A.target_qubit != B.target_qubit: return
  param = (A.param + B.param) % PI2
  #if param - PI > 1e-5: param = PI2 - param
  return IGate(A.name, A.target_qubit, param)

def settle_circuit(circuit:ICircuit) -> SettleResult:
  score = 0
  n_fuse = 0
  n_elim = 0

  # gates -> wires
  wires: List[List[LGate]] = [[] for _ in range(circuit.n_qubit)]
  depths = [0] * circuit.n_qubit
  for igate in circuit.gates:
    # score flag
    is_elim = False
    is_fuse = False

    # circuit
    is_Q2 = igate.control_qubit is not None
    wire_t: List[LGate] = wires[igate.target_qubit]
    wire_c: List[LGate] = wires[igate.control_qubit] if is_Q2 else None
    lgate_t = wire_t[-1] if wire_t else None
    lgate_c = wire_c[-1] if wire_c else None
    if is_Q2:
      if lgate_t is lgate_c and lgate_t is not None:    # objective eqivalent!
        if is_dagger(lgate_t.gate, igate):   # elim
          is_elim = True
          wire_t.remove(lgate_t)
          wire_c.remove(lgate_c)
          depths[igate.target_qubit]  -= 1
          depths[igate.control_qubit] -= 1
      if not is_elim:                        # append
        d = max(depths[igate.target_qubit], depths[igate.control_qubit]) + 1
        depths[igate.target_qubit] = depths[igate.control_qubit] = d
        lgate = LGate(d, igate)
        wire_t.append(lgate)
        wire_c.append(lgate)
    else:  # Q1
      if lgate_t is not None:
        if is_dagger(lgate_t.gate, igate):   # elim
          is_elim = True
          wire_t.remove(lgate_t)
          depths[igate.target_qubit] -= 1
        else:
          igate_fused = merge_rot_if_possible(lgate_t.gate, igate)
          if igate_fused is not None:        # fuse
            is_fuse = True
            wire_t.remove(lgate_t)
            wire_t.append(LGate(depths[igate.target_qubit], igate_fused))
      if not is_elim and not is_fuse:        # append
        d = depths[igate.target_qubit] + 1
        depths[igate.target_qubit] = d
        wire_t.append(LGate(d, igate))

    # score
    if is_elim:
      n_elim += 1
      score += int(GameConst.score_gate[igate.name] * GameConst.score_ratio_gate_eliminate)
    elif is_fuse:
      n_fuse += 1
      score += int(GameConst.score_gate[igate.name] * GameConst.score_ratio_gate_fuse)

  # wires -> gates
  gates_new: List[IGate] = []
  d = 1
  while d <= max(depths):
    for wire in wires:
      if not wire: continue
      lgate = wire[0]
      if lgate.depth > d: continue
      igate = lgate.gate
      if igate.control_qubit is not None:   # Q2 需要同时移除两个
        wire_t = wires[igate.target_qubit]
        wire_c = wires[igate.control_qubit]
        wire_t.remove(lgate)
        wire_c.remove(lgate)
      else:
        wire.pop(0)
      gates_new.append(igate)
    d += 1

  return SettleResult(ICircuit(circuit.n_qubit, gates_new), score, n_fuse, n_elim)


if __name__ == '__main__':
  circuit = ICircuit(2)
  circuit.append(IGate('Y', 0))
  circuit.append(IGate('H', 0))
  circuit.append(IGate('H', 0))
  circuit.append(IGate('RZ', 0, +PI_4))
  circuit.append(IGate('RZ', 0, -PI_4))
  circuit.append(IGate('RX', 1, +PI_4))
  circuit.append(IGate('RX', 1, +PI_4))
  circuit.append(IGate('RX', 1, +PI_4))
  circuit.append(IGate('CNOT', 0, control_qubit=1))
  circuit.append(IGate('CNOT', 0, control_qubit=1))
  circuit.append(IGate('CNOT', 1, control_qubit=0))
  ret = settle_circuit(circuit)
  print('circuit:', ret.circuit)
  print('score:', ret.score)
  print('n_fuse:', ret.n_fuse)
  print('n_elim:', ret.n_elim)
