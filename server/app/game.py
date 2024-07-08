#!/usr/bin/env python3
# Author: Armit
# Create Time: 2024/07/07 

from __future__ import annotations

from enum import Enum
from uuid import uuid1
from time import time
from typing import List, Set, Dict, Any

from app.circuit import *
from app.sdata import GameConst
from app.utils import HandlerRet


class GameState(Enum):
  INIT = 'INIT'
  RUN  = 'RUN'
  END  = 'END'


class Game:

  INSTANCES: Dict[int, Game] = {}

  def __init__(self):
    # playerdata
    self.id = str(uuid1())
    self.state = GameState.INIT
    self.circuit = ICircuit()
    self.cur_gate: List[IGate] = []
    self.nxt_gate: IGate = None
    self.score = 0
    self.token = 0
    self.bingo = 0
    self.n_qubit = GameConst.n_qubit
    self.n_depth = GameConst.n_depth
    self.ts_start = int(time())
    self.ts_end = -1
    # meta track
    self.INSTANCES[self.id] = self

  def json(self, pick:Set[str]=None) -> Dict[str, Any]:
    playerdata = {
      'id': self.id,
      'state': self.state,
      'circuit': self.circuit.json(),
      'cur_gate': [g.json() for g in self.cur_gate],
      'nxt_gate': self.nxt_gate.json(),
      'score': self.score,
      'token': self.token,
      'bingo': self.bingo,
      'n_qubit': self.n_qubit,
      'n_depth': self.n_depth,
      'ts_start': self.ts_start,
      'ts_end': self.ts_end,
    }
    if pick is None:
      return playerdata
    else:
      return {k: v for k, v in playerdata.items() if k in pick}

  def shift_gate_queue(self) -> bool:
    cur_gate_len = 0
    for lim, len in GameConst.cur_gate_len_lv:
      if self.score > lim:
        cur_gate_len = len

    while len(self.cur_gate) < cur_gate_len:
      if self.nxt_gate is not None:
        self.cur_gate.append(self.nxt_gate)
        self.nxt_gate = None
      else:
        self.cur_gate.append(rand_gate())
    if self.nxt_gate is None:
      self.nxt_gate = rand_gate()
  
  def handle_game_create(self) -> HandlerRet:
    # check
    assert self.state == GameState.INIT

    self.state = GameState.RUN
    self.shift_gate_queue()
    return HandlerRet(playerdata=self.json())

  def handle_game_settle(self) -> HandlerRet:
    self.state = GameState.END
    self.ts_end = int(time())
    return HandlerRet(playerdata=self.json(['state', 'ts_end']))

  def handle_game_put(self, idx:int, target_qubit:int, control_qubit:int=None) -> HandlerRet:
    # check
    assert idx > 0 and idx < len(self.cur_gate)
    assert target_qubit > 0 and target_qubit < self.n_qubit
    if control_qubit is not None:
      assert control_qubit > 0 and control_qubit < self.n_qubit
    assert self.state == GameState.RUN

    # player data change marker
    pick = set()

    # settle circuit operation
    gate = self.cur_gate.pop(idx)
    pick.add('cur_gate')
    ret = settle_circuit(self.circuit, IGate(gate.name, gate.param, target_qubit, control_qubit))
    self.circuit = ret.circuit
    pick.add('circuit')
    self.score += ret.score
    pick.add('score')
    if ret.type == SettleType.Eliminate:
      self.bingo += 1
      pick.add('bingo')
      if self.bingo % GameConst.reward_token_every_k_bingo == 0:
        self.token += 1
        pick.add('token')

    # next round
    self.shift_gate_queue()
    pick.add('cur_gate')
    pick.add('nxt_gate')

    # check dead
    if check_circuit_full(self.circuit, self.cur_gate, self.n_qubit, self.n_depth):
      self.state = GameState.END
      pick.add('state')
      self.ts_end = int(time())
      pick.add('ts_end')
    return HandlerRet(data={'settle_type': ret.type.value}, playerdata=self.json(pick))

  def handle_game_hint(self) -> HandlerRet:
    # check
    assert self.state == GameState.RUN
    assert self.token >= 1
    self.token -= 1

    hint_cases = []
    for idx, gate in enumerate(self.cur_gate):
      control_qubits = [None] if gate.name in D_GATE else range(self.n_qubit)
      for target_qubit in range(self.n_qubit):
        for control_qubit in control_qubits:
          if target_qubit == control_qubit: continue

          ret = settle_circuit(self.circuit, IGate(gate.name, gate.param, target_qubit, control_qubit))
          if ret.type == SettleType.Append: continue

          hint_case = {
            'idx': idx,
            'target_qubit': target_qubit,
            'settle_type': ret.type.value,
            'effected_gates': ret.effected_gates,
            'score': ret.score,
          }
          if control_qubit is not None:
            hint_case['control_qubit'] = control_qubit
          hint_cases.append(hint_case)

    return HandlerRet(data={'hint_cases': hint_cases}, playerdata=self.json({'token'}))
