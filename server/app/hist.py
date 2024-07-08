#!/usr/bin/env python3
# Author: Armit
# Create Time: 2024/07/08

import json
from threading import RLock
from typing import List, Literal, Union, NamedTuple
from app.utils import LOG_PATH

HIST_FILE = LOG_PATH / 'hist.json'

OrderBy = Union[Literal['score'], Literal['bingo']]

lock = RLock()

def synchronized(fn):
  def wrapper(*args, **kwargs):
    with lock:
      return fn(*args, **kwargs)
  return wrapper


class Record(NamedTuple):
  name: str
  score: int
  bingo: int
  ts_end: int

class DB(NamedTuple):
  hist: List[Record] = []   # 所有游玩记录
  best: List[Record] = []   # 每个玩家 (按name唯一) 的最高记录


class Hist:

  def load_db() -> DB:
    if not HIST_FILE.exists():
      return DB()

    with open(HIST_FILE, 'r', encoding='utf-8') as fh:
      data = json.load(fh)
    return DB(
      [Record(*it) for it in data['hist']],
      [Record(*it) for it in data['best']],
    )

  def save_db(db:DB):
    HIST_FILE.parent.mkdir(exist_ok=True)
    with open(HIST_FILE, 'w', encoding='utf-8') as fh:
      return json.dump({
        'hist': db.hist,
        'best': db.best,
      }, fh, indent=None, ensure_ascii=False)

  @staticmethod
  @synchronized
  def update_record(record:Record) -> bool:
    # load
    db = Hist.load_db()
    # append hist
    db.hist.append(record)
    # update best
    is_new = False
    found: Record = None
    for idx, it in enumerate(db.best):
      if it.name == record.name:
        found = it
        break
    if found:
      if record.score > found.score:
        db.best[idx] = record
        is_new = True
    else:
      db.best.append(record)
      is_new = True
    # save
    Hist.save_db(db)
    return is_new

  @staticmethod
  @synchronized
  def get_list_hist(offset:int=0, limit:int=None) -> List[Record]:
    # load
    db = Hist.load_db()
    hist_list = db.hist
    # filter
    hist_list = hist_list[::-1]
    L = min(offset, len(hist_list))
    R = None if limit is None else (L + limit)
    return hist_list[L:R]

  @staticmethod
  @synchronized
  def get_list_rank(order_by:OrderBy='score', limit:int=None) -> List[Record]:
    # load
    db = Hist.load_db()
    best_list = db.best
    # filter
    if order_by == 'score':
      best_list.sort(key=lambda it: it.score, reverse=True)
    elif order_by == 'bingo':
      best_list.sort(key=lambda it: it.bingo, reverse=True)
    else:
      raise ValueError(f'>> unknown order_by: {order_by}')
    return best_list[:limit]


if __name__ == '__main__':
  # 单元测试
  HIST_FILE = LOG_PATH / 'hist-test.json'
  HIST_FILE.parent.mkdir(exist_ok=True)
  HIST_FILE.unlink(missing_ok=True)

  # 初始空状态
  assert len(Hist.get_list_hist()) == 0

  # 来了一个玩家A
  Hist.update_record(Record('A', 50, 3, ts_end=100))
  assert len(Hist.get_list_hist()) == 1
  rank_list = Hist.get_list_rank()
  assert len(rank_list) == 1
  assert rank_list[0].name == 'A' and rank_list[0].score == 50

  # 他刷新了自己的记录
  Hist.update_record(Record('A', 100, 4, ts_end=200))
  assert len(Hist.get_list_hist()) == 2
  rank_list = Hist.get_list_rank()
  assert len(rank_list) == 1
  assert rank_list[0].name == 'A' and rank_list[0].score == 100
  
  # 来了一个玩家B，他比A牛逼
  Hist.update_record(Record('B', 150, 9, ts_end=300))
  assert len(Hist.get_list_hist()) == 3
  rank_list = Hist.get_list_rank()
  assert len(rank_list) == 2
  assert rank_list[0].name == 'B' and rank_list[0].score == 150
  assert rank_list[1].name == 'A' and rank_list[1].score == 100

  # A不服气，试了几次又反超回去了
  Hist.update_record(Record('A', 120, 5, ts_end=400))
  Hist.update_record(Record('A', 140, 6, ts_end=500))
  Hist.update_record(Record('A', 233, 7, ts_end=600))
  assert len(Hist.get_list_hist()) == 6
  rank_list = Hist.get_list_rank()
  assert len(rank_list) == 2
  assert rank_list[0].name == 'A' and rank_list[0].score == 233
  assert rank_list[1].name == 'B' and rank_list[1].score == 150

  # 但是A的bingo还是不如B多
  rank_list = Hist.get_list_rank('bingo')
  assert rank_list[0].name == 'B' and rank_list[0].bingo == 9
  assert rank_list[1].name == 'A' and rank_list[1].bingo == 7

  print('>> unit test passed!')
