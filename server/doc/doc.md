# API doc

----

⚪ Request & Response schema

```typescript
interface Request {
                           // 各API定义不同，详见后文
}
interface Response {
  code: int                // 状态码
  msg: str                 // 状态说明
  data?: ResponseData      // 各API定义不同，详见后文 (多数 API 的 data 都是空的)
  playerdata?: PlayerData  // 玩家存档状态的差分 (多数 API 都会修改部分存档)
}
```

⚪ Playerdata & Auxiliary schema

```typescript
enum GameState {
  INIT = 'INIT'
  RUN  = 'RUN'
  END  = 'END'
}

enum SettleType {
  Append    = 'Append'
  Fuse      = 'Fuse'
  Eliminate = 'Eliminate'
}

// schema: [gate_name, param, target_qubit, control_qubit]
// e.g.: 
//   ["H", null, 0, null]
//   ["RX", 2.33, 1, null]
//   ["CNOT", null, 0, 1]
type IGate = [str, float | null, int, int | null]

interface PlayerData {
  id: str             // 游戏ID
  state: GameState    // 游戏阶段状态
  circuit: IGate[]    // 当前线路构筑
  cur_gate: IGate[]   // 当前可拖动的门
  nxt_gate: IGate     // 预备可用的门
  score: int          // 当前得分
  token: int          // 提示道具数量
  bingo: int          // 消去次数
  n_qubit: int        // 当前线路宽度
  n_depth: int        // 当前线路最大深度
  ts_start: int       // 开局时间
  ts_end: int         // 结束时间
}

// schema: [player_name, score, bingo, ts_end]
type Record = [str, int, int, int]
```

----

### POST /game/create 开始游戏

```typescript
interface Request {

}
interface ResponseData {

}
```

### POST /game/settle 结束游戏

```typescript
interface Request {
  id: str               // 游戏ID
  name: str | null      // 玩家昵称，留空会随机生成
}
interface ResponseData {

}
```

### POST /game/put 放置门

```typescript
interface Request {
  id: str               // 游戏ID
  idx: int              // 选择 cur_gate 的下标
  target_qubit: int
  control_qubit?: int
}
interface ResponseData {
  settle_type: SettleType
}
```

### POST /game/hint 给予提示

```typescript
interface Request {
  id: str                     // 游戏ID
}
interface ResponseData {
  hint_cases: [               // 发生合并/消去的情况
    {
      idx: int                // 选择 cur_gate 的下标
      target_qubit: int
      control_qubit?: int
      settle_type: SettleType
      effected_gates: int[]   // 受影响的门在 circuit 中的下标列表
      score: int              // 预计得分
    }
  ]
}
```

----

### GET [/hist/list](/hist/list) 查看历史游戏记录

```typescript
interface Request {
  offset: int = 0     // page offset
  limit: int = 30     // page size
}
interface ResponseData {
  hist: Record[]
}
```

### GET [/hist/rank](/hist/rank) 查看最高分榜单

```typescript
interface Request {
  order_by: str = 'score'   // 'score' or 'bingo'
  limit: int = 30           // top k
}
interface ResponseData {
  rank: Record[]
}
```
