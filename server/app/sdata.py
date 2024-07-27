#!/usr/bin/env python3
# Author: Armit
# Create Time: 2024/07/08 

import numpy as np

class GameConst:
  # 线路宽度
  n_qubit = 5
  # 线路长度
  n_depth = 10
  # 手牌长度
  cur_gate_len_lv = [
    (0,    1),
    (750,  2),
    (3000, 3),
  ]
  # 量子门的随机生成权重
  gate_pool = {
    'H': 10,
    'X': 10,
    'Y': 10,
    'Z': 10,
    'X2P': 10,
    'X2M': 10,
    'Y2P': 10,
    'Y2M': 10,
    'T': 0,
    'TD': 0,
    'S': 10,
    'SD': 10,
    'RX': 25,
    'RY': 25,
    'RZ': 25,
    'CNOT': 15,
    'CZ': 15,
    'SWAP': 5,
    'iSWAP': 5,
  }
  gate_pool_names = list(gate_pool.keys())
  gate_pool_weights = np.asarray(list(gate_pool.values()))
  gate_pool_probs = (gate_pool_weights / gate_pool_weights.sum()).tolist()
  # 旋转门的随机转角 (以 π/4 为单位)
  rand_gate_rot = [-4, -2, 2, 4]
  rand_gate_rot_unit = np.pi / 4
  # 量子门基础分值
  score_gate = {
    'H': 5,
    'X': 5,
    'Y': 5,
    'Z': 5,
    'X2P': 10,
    'X2M': 10,
    'Y2P': 10,
    'Y2M': 10,
    'T': 10,
    'TD': 10,
    'S': 10,
    'SD': 10,
    'RX': 20,
    'RY': 20,
    'RZ': 20,
    'CNOT': 20,
    'CZ': 20,
    'SWAP': 20,
    'iSWAP': 30,
  }
  # 量子门追加得分倍率
  score_ratio_gate_append = 1.0
  # 量子门融合得分倍率
  score_ratio_gate_fuse = 1.25
  # 量子门消解得分倍率
  score_ratio_gate_eliminate = 3
  # 每 bingo 多少次，奖励一个 removal token
  reward_token_every_k_bingo = 10
