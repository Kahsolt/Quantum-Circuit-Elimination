/*--------- Env ---------*/
const HOST = '127.0.0.1';
const PORT = 8088;
const API_BASE = `http://${HOST}:${PORT}`;

const BG = 'w3-sand';  // main background color
const SP = '　';       // placeholder for the fucking css alignment :(
const TSIZE = 15;      // text font size
const BSIZE = 75;      // gate block size
const BGAP = 2;        // gate block margin
const PI = 3.14159265358979;
const CUR_GATE_MAX = 3;
var N_QUBIT = 5;
var N_DEPTH = 10;
const D_GATE = ['CNOT', 'CZ', 'SWAP'];

var playername = Math.random().toString(36).slice(-8).toUpperCase();
var playerdata = null;
var dragging_block = null;
var line_end_blocks = [];
var is_selecting_ctrlbit = false;
var is_selecting_ctrlbit_tmp_info = null;
var is_selecting_ctrlbit_blocks = [];
var is_selecting_ctrlbit_valid_row = [];

const $ = id => document.getElementById(id);
const $new = tag => document.createElement(tag);
const $newF = () => document.createDocumentFragment();
const $replace = (id, sRoot) => {
  const elem = document.getElementById(id);
  elem.innerText = '';
  elem.appendChild(sRoot);
};

/*--------- DOM ---------*/
function gate2str(gate) {
  if (!gate) return SP;
  let s = gate[0];
  if (gate[1]) {
    const coeff = Math.round(gate[1] / PI * 10) / 10;
    if      (Math.abs(coeff - 1  ) < 1e-5) s += `(π)`;
    else if (Math.abs(coeff - 1/2) < 1e-5) s += `(π/2)`;
    else if (Math.abs(coeff + 1/2) < 1e-5) s += `(-π/2)`;
    else if (Math.abs(coeff + 1  ) < 1e-5) s += `(-π)`;
  }
  return s;
}

function get_circuit_depth() {
  const depth = new Array(N_QUBIT).fill(0);
  if (!playerdata) return depth;

  for (gate of playerdata.circuit) {
    const [_, __, u, v] = gate;
    if (v == null) {
      depth[u]++;
    } else {
      const D = Math.max(depth[u], depth[v]);
      depth[u] = depth[v] = D + 1;
    }
  }
  return depth;
}

function updateGateList() {
  // curGate
  const sRoot = $newF();
  for (let i = 0; i < CUR_GATE_MAX; i++) {
    const txt = gate2str(playerdata?.cur_gate[i]);
    const isGate = txt !== SP;
    const color = isGate ? 'w3-light-green w3-hover-green' : BG;
    const block = $new('div');
    const cursor = isGate ? 'cursor: grab;' : '';
    block.id = `gate_${i}`;
    block.innerText = txt;
    block.style = `font-size: ${TSIZE}px; width: ${BSIZE}px; height: ${BSIZE}px; line-height: ${BSIZE}px; margin: ${BGAP}px; ${cursor}`;
    block.className = `w3-card ${color} w3-hoverable w3-center w3-show-inline-block`;
    block.draggable = isGate;
    if (block.draggable) {
      // https://web.dev/articles/drag-and-drop?hl=zh-cn
      block.addEventListener('dragstart', e => {
        dragging_block = e.target;
        e.target.style.opacity = 0.4;
      });
      block.addEventListener('dragend', e => {
        e.target.style.opacity = 1.0;
      });
    }
    sRoot.appendChild(block);
  }
  $replace('divCurGate', sRoot);

  // nxtGate
  const txt = gate2str(playerdata?.nxt_gate);
  const color = txt !== SP ? 'w3-light-grey w3-hover-grey' : BG;
  const block = $new('div');
  block.innerText = txt;
  block.style = `font-size: ${TSIZE}px; width: ${BSIZE}px; height: ${BSIZE}px; line-height: ${BSIZE}px; margin: ${BGAP}px; cursor: not-allowed;`;
  block.className = `w3-card ${color} w3-hoverable w3-center w3-show-inline-block`;
  $replace('divNxtGate', block);
}

function updateCircuit() {
  const grid = [];
  for (let r = 0; r < N_QUBIT; r++) {
    const row = [];
    for (let c = 0; c < N_DEPTH; c++) {
      const block = $new('div');
      block.id = `grid_${r}_${c}`;
      block.innerText = SP;
      block.style = `font-size: ${TSIZE}px; width: ${BSIZE}px; height: ${BSIZE}px; line-height: ${BSIZE}px; margin: ${BGAP}px;`;
      block.className = `w3-card ${BG} w3-hoverable w3-center w3-show-inline-block`;
      block.addEventListener('dragenter', e => {
        const target_qubit = parseInt(e.target.id.split('_')[1]);
        const depth = get_circuit_depth();
        const line_end_idx = depth[target_qubit];
        el_block = $(`grid_${target_qubit}_${line_end_idx}`);
        el_block.classList.add('w3-grey');
        line_end_blocks.push(el_block);
      });
      block.addEventListener('dragleave', e => {
        for (const el_block of line_end_blocks) {
          el_block.classList.remove('w3-grey');
        }
        line_end_blocks.clear();
      });
      block.addEventListener('dragover', e => e.preventDefault());
      block.addEventListener('drop', e => {
        const idx = parseInt(dragging_block.id.split('_')[1]);
        const target_qubit = parseInt(e.target.id.split('_')[1]);
        const isSingle = !D_GATE.includes(playerdata.cur_gate[idx].name);
        if (isSingle) {   // 单比特门直接确认
          API_game_put(idx, target_qubit);
          dragging_block = null;
        } else {          // 两比特门进入控制位选择状态
          const depth = get_circuit_depth();
          const refD = depth[target_qubit];
          for (let r = 0; r < N_QUBIT; r++) {
            if (target_qubit == r) continue;
            if (depth[r] <= refD) {
              const ctrl_block = grid[target_qubit][c];
              ctrl_block.classList.add('w3-grey');
              is_selecting_ctrlbit_blocks.push(ctrl_block);
              is_selecting_ctrlbit_valid_row.push(r);
            }
          }
          is_selecting_ctrlbit_tmp_info = [idx, target_qubit];  // 暂存
          is_selecting_ctrlbit = true;
        }
      });
      block.addEventListener('click', e => {   // 双比特门选择控制位
        // 必须是同列上合法的位置
        const control_qubit = parseInt(e.target.id.split('_')[1]);
        if (!is_selecting_ctrlbit_valid_row.includes(control_qubit)) return;

        // 左键确认；右键取消
        if (e.button == 0) {
          const [idx, target_qubit] = is_selecting_ctrlbit;
          API_game_put(idx, target_qubit, control_qubit);
          dragging_block = null;
        }
        is_selecting_ctrlbit = false;
        is_selecting_ctrlbit_tmp_info = null;
        for (const ctrl_block of is_selecting_ctrlbit_blocks) {
          ctrl_block.classList.remove('w3-grey');
        }
        is_selecting_ctrlbit_blocks.clear();
        is_selecting_ctrlbit_valid_row.clear();
      });
      row.push(block);
    }
    grid.push(row);
  }

  if (playerdata) {
    const depth = new Array(playerdata.n_qubit).fill(0);
    for (const gate of playerdata.circuit) {
      const [name, param, u, v] = gate;
      const txt = gate2str(gate);
      let block = null;
      if (v != null) {
        const D = Math.max(depth[u], depth[v]);
        depth[u] = depth[v] = D + 1;
        for (block of [grid[u][D], grid[v][D]]) {
          block.innerText = txt;
          block.classList.remove(BG);
          block.classList.add('w3-blue');
        }
      } else {
        const D = depth[u];
        depth[u]++;
        block = grid[u][D];
        block.innerText = txt;
        block.classList.remove(BG);
        block.classList.add('w3-blue');
      }
    }
  }

  const sRoot = $newF();
  for (let r = 0; r < N_QUBIT; r++) {
    const wire = $new('div');
    for (let c = 0; c < N_DEPTH; c++) {
      wire.appendChild(grid[r][c]);
    }
    sRoot.appendChild(wire);
  }
  $replace('divCircuit', sRoot);
}

function updateScoreBoard() {
  $('score').innerText = playerdata ? playerdata.score : 0;
  $('token').innerText = playerdata ? playerdata.token : 0;
  $('bingo').innerText = playerdata ? playerdata.bingo : 0;
  $('player').value = playername;
}

function updateRanklist(ranklist, showAlert=false) {
  // shadow DOM construct
  const sRoot = $newF();
  // table header
  const tr = $new('tr');
  for (const col of ['name', 'score', 'bingo', 'ts']) {
    const th = $new('th');
    th.innerText = col;
    tr.appendChild(th);
  }
  sRoot.appendChild(tr);
  // table content
  for (const it of ranklist) {
    const tr = $new('tr');
    for (let i = 0; i < it.length; i++) {
      let v = it[i];
      if (i == 3) {
        const date = new Date(v * 1000);
        v = date.toLocaleDateString();
      }
      const td = $new('td');
      td.innerText = v;
      tr.appendChild(td);
    }
    sRoot.appendChild(tr);
  }
  // real DOM update
  $replace('tblRank', sRoot);
  // msgbox
  if (showAlert) alert('Refresh successful.')
}

function updateUI() {
  updateGateList();
  updateCircuit();
  updateScoreBoard();
}

function resetUI() {
  playerdata = null;
  updateUI();
  API_hist_rank();
}

function onBtnStart() {
  $('btnStart').classList.replace('w3-show', 'w3-hide');
  $('btnSettle').classList.replace('w3-hide', 'w3-show');
  API_game_create();
}

function onBtnSettle() {
  $('btnStart').classList.replace('w3-hide', 'w3-show');
  $('btnSettle').classList.replace('w3-show', 'w3-hide');
  API_game_settle();
}

function onBtnRankRefrsh() {
  API_hist_rank(true);
}

/*--------- HTTP ---------*/

function GET(ep, args={}, callback=null) {
  let query = '';
  if (args) {
    query += '?'
    for (const k in args) {
      query += k + '=' + args[k] + '&';
    }
    query = query.substring(0, query.length - 1);   // trim tailing '&'
  }
  const url = ep + query;
  console.log(`[GET ${url}]`);
  axios.get(
    `${API_BASE}${ep}${query}`
  )
  .then(r => {
    const rdata = r.data;
    console.log(`[GET ${url}] resp: %o`, rdata);
    if (rdata.code != 200) {
      alert(JSON.stringify(rdata));
      return;
    }
    if (callback) callback(rdata.data || {});
  })
  .catch(e => {
    console.log('[GET] err: %o', e);
  })
}

function POST(ep, data={}, callback=null) {
  if (playerdata) {
    data.id = playerdata.id
  }
  console.log(`[POST ${ep}] req: %o`, data);
  axios.post(
    `${API_BASE}${ep}`, data
  )
  .then(r => {
    const rdata = r.data;
    console.log(`[POST ${ep}] resp: %o`, rdata);
    if (rdata.code != 200) {
      alert(JSON.stringify(r));
      return;
    }
    const delta = rdata.playerdata;
    if (delta) {
      if (!playerdata) playerdata = {};
      for (const k in delta) {
        playerdata[k] = delta[k];
      }
    }
    if (callback) callback(rdata.data || {});
  })
  .catch(e => {
    console.log('[POST] err: %o', e);
  })
}

function API_game_create() {
  if (playerdata) return;

  POST('/game/create', {}, r => {
    updateUI();
    N_QUBIT = playerdata.n_qubit;
    N_DEPTH = playerdata.n_depth;
  });
}

function API_game_settle() {
  if (!playerdata) return;

  POST('/game/settle', {
    'name': $('player').value,
  }, r => {
    resetUI();
  });
}

function API_game_put(idx, target_qubit, control_qubit=null) {
  POST('/game/put', {
    'idx': idx,
    'target_qubit': target_qubit,
    'control_qubit': control_qubit,
  }, r => {
    updateUI();
  })
}

function API_game_del(idx) {
  POST('/game/del', {
    'idx': idx,
  }, r => {
    updateUI();
  });
}

function API_cheat_item(item, count=10) {
  POST('/cheat/item', {
    'item': item,
    'count': count,
  }, r => {
    updateScoreBoard();
  });
}

function API_hist_rank(show_alert=false) {
  GET('/hist/rank', {
    'limit': 15,
  }, r => {
    updateRanklist(r.rank, show_alert);
  });
}
