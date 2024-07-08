#!/usr/bin/env python3
# Author: Armit
# Create Time: 2024/07/08 

from __future__ import annotations

import random
from copy import deepcopy
from dataclasses import dataclass, field
from typing import List, Union, Optional, NamedTuple

import numpy as np
from numpy import pi
from app.sdata import GameConst

D_GATE = ['CZ', 'CNOT', 'SWAP', 'iSWAP']
P_GATE = ['RX', 'RY', 'RZ']


@dataclass
class XGate:
  name: str
  param: Optional[float] = None

  def clone(self) -> IGate:
    return deepcopy(self)

  def json(self):
    return [self.name, self.param]


@dataclass
class IGate:
  name: str
  param: Optional[float] = None
  target_qubit: Optional[int] = None
  control_qubit: Optional[int] = None

  def clone(self) -> IGate:
    return deepcopy(self)

  def json(self):
    return [self.name, self.param, self.target_qubit, self.control_qubit]


@dataclass
class ICircuit:
  gates: List[IGate] = field(default_factory=list)

  def __len__(self) -> int:
    return len(self.gates)

  def __getitem__(self, idx:int) -> IGate:
    return self.gates[idx]

  def append(self, g:IGate):
    self.gates.append(g)

  def remove(self, idx:Union[int, List[int]]):
    if not isinstance(idx, list): idx = [idx]
    self.gates = [g for i, g in enumerate(self.gates) if i not in idx]

  def clone(self) -> ICircuit:
    return deepcopy(self)

  def json(self):
    return [g.json() for g in self.gates]


class SettleType:
  Append = 'Append'
  Fuse = 'Fuse'
  Eliminate = 'Eliminate'


class SettleResult(NamedTuple):
  type: SettleType
  circuit: int
  effected_gates: List[int] = []
  score: int = 0


def rand_gate() -> XGate:
  names = GameConst.gate_pool_names
  prob = GameConst.gate_pool_probs
  name = np.random.choice(names, p=prob)
  param = (random.choice(GameConst.rand_gate_rot) / 4 * pi) if name in P_GATE else None
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


def check_gate_put(circuit:ICircuit, gate:IGate, n_qubit:int, max_depth:int) -> bool:
  depth = get_circuit_depth(circuit, n_qubit)
  if gate.control_qubit is not None:
    D = max(depth[gate.target_qubit], depth[gate.control_qubit]) + 1
  else:
    D = depth[gate.target_qubit] + 1
  return D <= max_depth


def check_circuit_full(circuit:ICircuit, gates:List[IGate], n_qubit:int, max_depth:int) -> bool:
  depth = get_circuit_depth(circuit, n_qubit)
  has_single = False
  for gate in gates:
    if gate.name not in D_GATE:
      has_single = True
      break
  return sum([max_depth - d for d in depth]) < (1 if has_single else 2)


def settle_circuit(circuit:ICircuit, gate:IGate) -> SettleResult:
  # TODO： 结算线路操作
  # settle order: Eliminate -> Fuse -> Append

  #effected_qubits = [it for it in [gate.target_qubit, gate.control_qubit] if it is not None]
  #effected_gates = try_collapse_circuit(circuit, effected_qubits)

  circuit_new = circuit.clone()
  circuit_new.append(gate)
  score = int(GameConst.score_gate[gate.name] * GameConst.score_ratio_gate_append)
  effected_gates = [len(circuit_new)]

  return SettleResult(SettleType.Append, circuit_new.clone(), effected_gates, score)


def try_collapse_circuit(circuit:ICircuit, effected_qubits:List[int]) -> List[int]:
  # TODO: 判断线路 circuit 中是否存在可对消的子线路，返回子线路的门在 circuit 列表中的下标
  # effected_qubit 是该线路最后一次改动，暂时不知道这个信息是否有助于搜索剪枝
  return []
