#!/usr/bin/env python3
# Author: Armit
# Create Time: 2024/07/07 

from argparse import ArgumentParser

from flask import Flask, render_template, request
from app.game import Game, GameState
from app.hist import Hist, Record
from app.utils import WWWROOT, HandlerRet, resp_ok, resp_error, rand_string

app = Flask(
  __file__,
  template_folder=WWWROOT,
  static_folder=WWWROOT,
  static_url_path='',
)


@app.route('/', methods=['GET'])
def root():
  return render_template('doc.html')


@app.route('/game/create', methods=['POST'])
def game_create():
  game = Game()
  game.handle_game_create()
  return resp_ok(playerdata=game.json())


@app.route('/game/settle', methods=['POST'])
def game_settle():
  try:
    rdata = request.json
    game = Game.INSTANCES[rdata['id']]

    name = rdata.get('name', f'Anonymous-{rand_string()}')
    assert isinstance(name, str) and len(name)

    ret = game.handle_game_settle()
    is_new = Hist.update_record(Record(name, game.score, game.bingo, game.ts_end))
    ret.data = {'is_new': is_new}
    resp = resp_ok(ret)

    del Game.INSTANCES[game.id]
    return resp
  except Exception as e:
    return resp_error(msg=e)


@app.route('/game/put', methods=['POST'])
def game_put():
  try:
    rdata = request.json
    game = Game.INSTANCES[rdata['id']]

    idx = rdata['idx']
    assert isinstance(idx, int)
    target_qubit = rdata['target_qubit']
    assert isinstance(target_qubit, int)
    control_qubit = rdata.get('control_qubit')
    if control_qubit is not None:
      assert isinstance(control_qubit, int)

    return game.handle_game_put(idx, target_qubit, control_qubit)
  except Exception as e:
    return resp_error(msg=e)


@app.route('/game/hint', methods=['POST'])
def game_hint():
  try:
    rdata = request.json
    game = Game.INSTANCES[rdata['id']]

    return game.handle_game_hint()
  except Exception as e:
    return resp_error(msg=e)


@app.route('/hist/list', methods=['GET'])
def hist_list():
  try:
    rdata = request.args

    offset = rdata.get('offset', 0)
    assert isinstance(offset, int)
    assert offset >= 0
    limit = rdata.get('limit', 30)
    assert isinstance(limit, int)
    assert limit > 0 and limit <= 100

    hist_list = Hist.get_list_hist(offset, limit)
    return resp_ok(HandlerRet(data={'hist': hist_list}))
  except Exception as e:
    return resp_error(msg=e)


@app.route('/hist/rank', methods=['GET'])
def hist_rank():
  try:
    rdata = request.args

    order_by = rdata.get('order_by', 'score')
    assert order_by in ['score', 'bingo']
    limit = rdata.get('limit', 30)
    assert isinstance(limit, int)
    assert limit > 0 and limit <= 100

    rank_list = Hist.get_list_rank(order_by, limit)
    return resp_ok(HandlerRet(data={'rank': rank_list}))
  except Exception as e:
    return resp_error(msg=e)


if __name__ == '__main__':
  parser = ArgumentParser()
  parser.add_argument('-P', '--port', type=int, default=8088)
  args = parser.parse_args()

  app.run(host='0.0.0.0', port=args.port, debug=False)
