#!/usr/bin/env python3
# Author: Armit
# Create Time: 2024/07/07 

from argparse import ArgumentParser
from traceback import format_exc

from flask import Flask, render_template, request, Response
from app.game import Game
from app.hist import Hist, Record
from app.utils import WWWROOT, HandlerRet, resp_ok, resp_error, rand_string

app = Flask( __file__, template_folder=WWWROOT, static_folder=WWWROOT, static_url_path='')

# https://blog.csdn.net/hwhsong/article/details/84959755
def allow_CORS(resp:Response):
  resp.headers['Access-Control-Allow-Origin'] = '*'
  resp.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
  resp.headers['Access-Control-Allow-Headers'] = 'x-requested-with,content-type'
  return resp
app.after_request(allow_CORS)


@app.route('/', methods=['GET'])
def root():
  return render_template('doc.html')


@app.route('/game/create', methods=['POST'])
def game_create():
  try:
    game = Game()
    game.handle_game_create()
    return resp_ok(HandlerRet(playerdata=game.json()))
  except:
    return resp_error(format_exc())


@app.route('/game/settle', methods=['POST'])
def game_settle():
  try:
    rdata = request.json
    game = Game.INSTANCES[rdata['id']]

    name = rdata.get('name', rand_string())
    assert isinstance(name, str) and len(name) and len(name) <= 32

    ret = game.handle_game_settle()
    is_new = Hist.update_record(Record(name, game.score, game.bingo, game.ts_end))
    resp = resp_ok(HandlerRet(data={'is_new': is_new}, playerdata=ret.playerdata))

    del Game.INSTANCES[game.id]
    return resp
  except:
    return resp_error(format_exc())


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

    return resp_ok(game.handle_game_put(idx, target_qubit, control_qubit))
  except:
    return resp_error(format_exc())


@app.route('/game/del', methods=['POST'])
def game_del():
  try:
    rdata = request.json
    game = Game.INSTANCES[rdata['id']]

    idx = rdata['idx']
    assert isinstance(idx, int)

    return resp_ok(game.handle_game_del(idx))
  except:
    return resp_error(format_exc())


@app.route('/cheat/item', methods=['POST'])
def cheat_item():
  try:
    rdata = request.json
    game = Game.INSTANCES[rdata['id']]

    item = rdata['item']
    assert isinstance(item, str)
    count = rdata.get('count', 10)
    assert isinstance(count, int)

    return resp_ok(game.handle_cheat_item(item, count))
  except:
    return resp_error(format_exc())


@app.route('/hist/list', methods=['GET'])
def hist_list():
  try:
    rdata = request.args

    offset = int(rdata.get('offset', 0))
    assert offset >= 0
    limit = int(rdata.get('limit', 30))
    assert limit > 0 and limit <= 100

    hist_list = Hist.get_list_hist(offset, limit)
    return resp_ok(HandlerRet(data={'hist': hist_list}))
  except:
    return resp_error(format_exc())


@app.route('/hist/rank', methods=['GET'])
def hist_rank():
  try:
    rdata = request.args

    order_by = rdata.get('order_by', 'score')
    assert order_by in ['score', 'bingo']
    limit = int(rdata.get('limit', 30))
    assert limit > 0 and limit <= 100

    rank_list = Hist.get_list_rank(order_by, limit)
    return resp_ok(HandlerRet(data={'rank': rank_list}))
  except:
    return resp_error(format_exc())


if __name__ == '__main__':
  parser = ArgumentParser()
  parser.add_argument('-P', '--port', type=int, default=8088)
  args = parser.parse_args()

  app.run(host='0.0.0.0', port=args.port, debug=False)
