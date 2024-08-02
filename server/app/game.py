#!/usr/bin/env python3
# Author: Armit
# Create Time: 2024/07/07 

from __future__ import annotations

from uuid import uuid1
from time import time
from typing import List, Set, Dict, Any

from app.circuit import *
from app.sdata import GameConst
from app.utils import HandlerRet


class GameState:
  INIT = 'INIT'
  RUN  = 'RUN'
  END  = 'END'


class Game:

  INSTANCES: Dict[int, Game] = {}

  def __init__(self):
    # playerdata
    self.id = str(uuid1())
    self.state = GameState.INIT
    self.circuit = ICircuit(GameConst.n_qubit)
    self.cur_gate: List[XGate] = []
    self.nxt_gate: XGate = None
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
    for lim, nlen in GameConst.cur_gate_len_lv:
      if self.score >= lim:
        cur_gate_len = nlen

    while len(self.cur_gate) < cur_gate_len:
      if self.nxt_gate is not None:
        self.cur_gate.append(self.nxt_gate)
        self.nxt_gate = None
      else:
        self.cur_gate.append(rand_xgate())
    if self.nxt_gate is None:
      self.nxt_gate = rand_xgate()
  
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
    assert self.state == GameState.RUN
    assert 0 <= idx < len(self.cur_gate)
    gname = self.cur_gate[idx].name
    isSWAP = gname == 'SWAP'    # special case
    isSWAP_give_up = False      # 场上剩余门不够的情况下，自动放弃操作
    if isSWAP:
      if target_qubit == control_qubit == -1:
        isSWAP_give_up = True
      else:
        assert 0 <= target_qubit  < len(self.circuit)
        assert 0 <= control_qubit < len(self.circuit)
        igate_A = self.circuit[target_qubit]
        igate_B = self.circuit[control_qubit]
        assert igate_A.control_qubit is None
        assert igate_B.control_qubit is None
    else:
      if gname in D_GATE:
        assert control_qubit is not None
      else:
        assert control_qubit is None
      assert 0 <= target_qubit < self.n_qubit
      if control_qubit is not None:
        assert 0 <= control_qubit < self.n_qubit
        assert control_qubit != target_qubit

    # player data change marker
    pick = set()

    # operation
    xgate = self.cur_gate.pop(idx)
    pick.add('cur_gate')
    if isSWAP:    # swap location of two single-qubit gate
      if not isSWAP_give_up:
        gates = self.circuit.gates
        # 先交换指令位序
        tmp = gates[target_qubit]
        gates[target_qubit] = gates[control_qubit]
        gates[control_qubit] = tmp
        # 再交换所在线缆
        tmp = gates[target_qubit].target_qubit
        gates[target_qubit].target_qubit = gates[control_qubit].target_qubit
        gates[control_qubit].target_qubit = tmp
    else:         # append to circuit
      igate = IGate(xgate.name, target_qubit, xgate.param, control_qubit)
      assert check_gate_can_put(self.circuit, igate, self.n_qubit, self.n_depth)
      self.circuit.append(igate)
    # circuit
    ret = settle_circuit(self.circuit)
    self.circuit = ret.circuit
    pick.add('circuit')
    # fuse/elim => score
    self.score += ret.score
    # append => score
    if ret.n_elim == ret.n_fuse == 0:
      self.score += int(GameConst.score_gate[xgate.name] * GameConst.score_ratio_gate_append)
    pick.add('score')
    # bingo => token
    for _ in range(ret.n_elim):
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
    if check_circuit_is_full(self.circuit, self.cur_gate, self.n_qubit, self.n_depth):
      self.state = GameState.END
      pick.add('state')
      self.ts_end = int(time())
      pick.add('ts_end')
    return HandlerRet(playerdata=self.json(pick))

  def handle_game_del(self, idx:int) -> HandlerRet:
    # check
    assert self.state == GameState.RUN
    assert 0 <= idx < len(self.circuit)
    assert self.token >= 1

    # player data change marker
    pick = set()

    # token
    self.token -= 1
    pick.add('token')
    # circuit
    self.circuit.remove(idx)
    ret = settle_circuit(self.circuit)
    self.circuit = ret.circuit
    pick.add('circuit')
    # fuse/elim => score
    self.score += ret.score
    pick.add('score')
    # bingo => token
    for _ in range(ret.n_elim):
      self.bingo += 1
      pick.add('bingo')
      if self.bingo % GameConst.reward_token_every_k_bingo == 0:
        self.token += 1
        pick.add('token')
    return HandlerRet(playerdata=self.json(pick))

  def handle_cheat_item(self, item:str, count:int) -> HandlerRet:
    # check
    assert item in ['score', 'token']
    assert count > 0

    if item == 'score':
      self.score += count
    elif item == 'token':
      self.token += count
    return HandlerRet(playerdata=self.json({item}))
