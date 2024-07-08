#!/usr/bin/env python3
# Author: Armit
# Create Time: 2024/07/08 

import string
import random
from pathlib import Path
from flask import jsonify
from typing import Dict, Any, NamedTuple

BASE_PATH = Path(__name__).parent.parent
WWWROOT = BASE_PATH / 'doc'
LOG_PATH = BASE_PATH / 'log'


''' HTTP Utils '''

class HandlerRet(NamedTuple):
  data: Dict[str, Any] = {}
  playerdata: Dict[str, Any] = {}

RespData = Dict[str, Any]

def resp_ok(ret:HandlerRet) -> RespData:
  resp = {
    'code': 200,
    'msg': 'OK',
  }
  if ret.data:       resp['data']       = ret.data
  if ret.playerdata: resp['playerdata'] = ret.playerdata
  return jsonify(resp)

def resp_error(msg:str='invalid param', code:int=400) -> RespData:
  return jsonify({
    'code': code,
    'msg': msg,
  })


''' Misc Utils '''

RAND_STRING_POOL = string.ascii_uppercase + string.digits

def rand_string(nlen:int=8) -> str:
  return ''.join(random.choice(RAND_STRING_POOL) for _ in range(nlen))
