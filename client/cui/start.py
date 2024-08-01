#!/usr/bin/env python3
# Author: Armit
# Create Time: 2024/07/09 

import os
import sys
from pprint import pprint
from fractions import Fraction
from argparse import ArgumentParser
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Any

from math import pi
from requests import session

class DrawBackend:
  NONE = 'none'
  PENNYLANE = 'pennylane'
  PYQPANDA = 'pyqpanda'

DRAW_BACKEND = DrawBackend.NONE
try:
  import pennylane as qml
  IS_PENNYLANE_AVAILABLE = True
except ImportError:
  IS_PENNYLANE_AVAILABLE = False
try:
  import pyqpanda as pq
  from pyqpanda import CPUQVM, QCircuit
  IS_PYQPANDA_AVAILABLE = True
except ImportError:
  IS_PYQPANDA_AVAILABLE = False


D_GATES = ['CNOT', 'CZ', 'SWAP']
P_GATES = ['RX', 'RY', 'RZ']

@dataclass
class XGate:
  name: str
  param: float = None

  def __repr__(self):
    s = f'{self.name}'
    if self.param:
      frac = Fraction(round(self.param / pi, 2))
      a, b = frac.as_integer_ratio()
      if abs(a) == abs(b) == 1:
        s += f'(-π)' if self.param < 0 else f'(π)'
      else:
        s += f'({a}/{b}π)'
    return s

@dataclass
class IGate:
  name: str
  param: float = None
  target_qubit: int = None
  control_qubit: int = None

  def __repr__(self):
    s = f'{self.name}'
    s += f'(q{self.target_qubit}'
    if self.control_qubit is not None:
      s += f', q{self.control_qubit}'
    if self.param:
      frac = Fraction(round(self.param / pi, 2))
      a, b = frac.as_integer_ratio()
      if abs(a) == abs(b) == 1:
        s += f', -π' if self.param < 0 else f', π'
      else:
        s += f', {a}/{b}π'
    s += ')'
    return s

class State:
  INIT = 'INIT'
  RUN  = 'RUN'
  END  = 'END'

@dataclass
class PlayerData:
  id: str = None
  state = State.INIT
  circuit: List[IGate] = field(default_factory=list)
  cur_gate: List[XGate] = field(default_factory=list)
  nxt_gate: XGate = None
  score: int = -1
  token: int = -1
  bingo: int = -1
  n_qubit: int = -1
  n_depth: int = -1
  ts_start: int = -1
  ts_end: int = -1

playerdata: PlayerData = None
is_create: bool = None
is_debug: bool = None


ReqData = Dict[str, Any]
RspData = Dict[str, Any]

http = session()
last_request: Tuple[Any] = None

def POST(ep:str, req_data:ReqData=None) -> RspData:
  global http, last_request, playerdata, API_BASE, is_debug
  req_data = req_data or {}
  if playerdata is not None:
    req_data['id'] = playerdata.id
  resp = http.post(f'{API_BASE}{ep}', json=req_data)
  assert resp.ok, print(f'>> [POST {ep}] {resp.status_code} {resp.reason}')
  resp_data: RspData = resp.json()
  assert resp_data['code'] == 200, print(f'>> [POST {ep}] {resp_data["code"]} {resp_data["msg"]}')
  last_request = (ep, req_data, resp_data)
  delta = resp_data.get('playerdata')
  if delta:
    if playerdata is None:
      playerdata = PlayerData()
    for k, v in delta.items():
      if k == 'circuit':
        setattr(playerdata, k, [IGate(*it) for it in v])
      elif k == 'cur_gate':
        setattr(playerdata, k, [XGate(*it) for it in v])
      elif k == 'nxt_gate':
        setattr(playerdata, k, XGate(*v))
      else:
        setattr(playerdata, k, v)
  return resp_data.get('data')


def API_game_create():
  global is_create
  is_create = True
  resp = POST('/game/create')
  return resp

def API_game_settle():
  global is_create, args, playerdata
  if not is_create: return
  resp = POST('/game/settle', {
    'name': args.name,
  } if args.name else {})
  playerdata = None
  is_create = False
  return resp

def API_game_put(idx:int, target_qubit:int, control_qubit:int=None):
  resp = POST('/game/put', {
    'idx': idx,
    'target_qubit': target_qubit,
    'control_qubit': control_qubit,
  })
  return resp

def API_game_del(idx:int):
  resp = POST('/game/del', {
    'idx': idx,
  })
  return resp

def API_cheat_item(item:str, count:int):
  resp = POST('/cheat/item', {
    'item': item, 
    'count': count,
  })
  return resp


def clear_screen():
  if sys.platform == 'win32':
    os.system('CLS')
  else:
    os.system('clear')

def draw_circuit_pennylane():
  GATE_NAME_MAPPING = {
    'H': 'Hadamard',
  }
  dev = qml.device('default.qubit', wires=playerdata.n_qubit)
  @qml.qnode(dev)
  def circuit():
    for gate in playerdata.circuit:
      q = gate.target_qubit
      G = getattr(qml, GATE_NAME_MAPPING.get(gate.name, gate.name), None)
      if gate.name in D_GATES:
        G(wires=[gate.control_qubit, gate.target_qubit])
      elif gate.name in P_GATES:
        G(gate.param, wires=q)
      elif G is not None:
        G(wires=q)
      else:   # G is None, need translate
        if   gate.name == 'TD':  qml.RZ(-pi / 4, wires=q)
        elif gate.name == 'SD':  qml.RZ(-pi / 2, wires=q)
        else:
          print('>> unknown gate:', gate.name)
          breakpoint()
    return qml.state()
  print(qml.draw(circuit)())

def draw_circuit_pyqpanda():
  qvm = CPUQVM()
  qvm.init_qvm()
  qv = qvm.qAlloc_many(playerdata.n_qubit)
  qcir = QCircuit()
  for gate in playerdata.circuit:
    q = qv[gate.target_qubit]
    G = getattr(pq, gate.name, None)
    if gate.name in D_GATES:
      qcir << G(qv[gate.control_qubit], q)
    elif gate.name in P_GATES:
      qcir << G(q, gate.param)
    elif G is not None:
      qcir << G(q)
    else:   # G is None, need translate
      if   gate.name == 'TD':  qcir << pq.RZ(q, -pi / 4)
      elif gate.name == 'SD':  qcir << pq.RZ(q, -pi / 2)
      else:
        print('>> unknown gate:', gate.name)
        breakpoint()
  print(qcir)

def print_panel_help():
  clear_screen()
  print('[Meta Commands]')
  print(f'  help/?    show this command help')
  print(f'  quit      quit game')
  print(f'  reset     reset game')
  print(f'  debug     toggle debug mode (now: {"ON" if is_debug else "OFF"})')
  print(f'  #<code>   eval python code')
  print()
  print('[Game Commands]')
  print(f'  <idx> <target_qubit> [control_qubit]')
  print(f'      put the idx-th cur gate on target_qubit and (optional) control_qubit')
  print(f'  d <idx>')
  print(f'      delete the idx-th gate in circuit')
  print(f'  !<score|token> [count]')
  print(f'      cheat get item')
  print()
  input('>> press any key...')

def print_panel_main():
  global is_debug

  clear_screen()
  if playerdata is None: return

  if is_debug:
    print(f'[HTTP] {last_request[0]}')
    print('request:')
    pprint(last_request[1])
    print('response:')
    pprint(last_request[2])
    print('-' * 72)
    print('[PlayerData]')
    pprint(vars(playerdata))
    print('=' * 72)
    print()

  print('Current Circuit:')
  if DRAW_BACKEND == DrawBackend.NONE:
    pprint(playerdata.circuit)
    print()
  elif DRAW_BACKEND == DrawBackend.PENNYLANE:
    draw_circuit_pennylane()
    print()
  elif DRAW_BACKEND == DrawBackend.PYQPANDA:
    draw_circuit_pyqpanda()

  print('Cur Gate:', playerdata.cur_gate)
  print('Next Gate:', playerdata.nxt_gate)
  print('===================================')
  print('Score:', playerdata.score)
  print('Token:', playerdata.token)
  print()

def run():
  global is_debug
  cmd_retry = None
  try:
    API_game_create()
    while True:
      print_panel_main()
      if cmd_retry is not None:
        cmd = cmd_retry
        cmd_retry = None
      else:
        cmd = input('>> input your command (h for help): ').strip().lower()

      if not cmd: continue
      if cmd in ['quit', 'q', 'exit']: break
      if cmd in ['debug', 'd']:
        is_debug = not is_debug
        continue

      if cmd.startswith('#'):
        cmd = cmd[1:].strip()
        print(eval(cmd))
        continue
      if cmd in ['help', 'h', '?']:
        print_panel_help()
        continue

      if cmd in ['reset', 'r']:
        API_game_settle()
        API_game_create()
        continue

      if cmd.startswith('d'):
        idx = int(cmd.split(' ')[-1])
        API_game_del(idx)
        continue

      if cmd.startswith('!'):
        cmd = cmd[1:].strip()
        item, *args = cmd.split(' ')
        count = int(args[0]) if args else None
        API_cheat_item(item, count)
        continue

      try:
        segs = [int(e) for e in cmd.split(' ')]
        API_game_put(*segs)
      except Exception as e:
        cmd_retry = input(f'<< Error: bad command!!\n>> input your command (h for help): ')

  except KeyboardInterrupt:
    print('>> Exit by Ctrl+C')
  finally:
    API_game_settle()


if __name__ == '__main__':
  parser = ArgumentParser()
  parser.add_argument('-H', '--host', default='127.0.0.1', help='server ip')
  parser.add_argument('-P', '--port', default=8088, type=int, help='server port')
  parser.add_argument('-D', '--drawer', default='pennylane', choices=['auto', 'none', 'pennylane', 'pyqpanda'], help='circuit drawer')
  parser.add_argument('--name', help='player name')
  parser.add_argument('--debug', action='store_true', help='enable debug mode')
  args = parser.parse_args()

  API_BASE = f'http://{args.host}:{args.port}'

  if args.drawer == 'pennylane':
    assert IS_PENNYLANE_AVAILABLE, 'package "pennylane" not available'
    DRAW_BACKEND = DrawBackend.PENNYLANE
  elif args.drawer == 'pyqpanda':
    assert IS_PYQPANDA_AVAILABLE, 'package "pyqpanda" not available'
    DRAW_BACKEND = DrawBackend.PYQPANDA
  elif args.drawer == 'auto':
    if IS_PENNYLANE_AVAILABLE:
      DRAW_BACKEND = DrawBackend.PENNYLANE
    elif IS_PYQPANDA_AVAILABLE:
      DRAW_BACKEND = DrawBackend.PYQPANDA

  is_debug = args.debug

  run()
