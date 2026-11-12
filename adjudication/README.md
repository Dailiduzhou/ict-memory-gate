# 裁决包（v0.1 首轮 A／B 双标 → 待裁决 54 条）

由 `python3 adjudication/build-pack.py` 生成，可重复生成、不覆盖任何原始标注。
输入：`annotations/A-v0.1.csv`、`annotations/b-v0.1.csv`、`cases/*.jsonl`。
**本目录不修改 `cases/`、不修改两份原始标注 CSV。**

**裁决人：邱振豪（规则作者，非 A／B 标注者）＋ 杨冰冰（标注者 A，非规则作者）** —— 符合 rubric §二.6“规则作者＋非作者”；季星辰（B）不参与裁决，其 `note` 已在 `adjudication-sheet.csv` 中供参考。

**利益冲突声明**：杨冰冰是当事标注者 A，邱振豪是草案标签作者。因此流程强制：pass 1 两人**各自独立**、互不可见、**不看 A／B 判定也不看草案**；P0 三条必须两人一致才闭合；pass 3 之前不得打开 `draft-reference.csv`。

## 文件

| 文件 | 内容 | 何时可看 |
|---|---|---|
| `adjudication-material.jsonl` | 54 条争议用例的盲输入（`group`＋`case_id`＋类别＋来源／候选／旧记忆／删除状态／请求者／读取请求），**不含 `expected`／`notes`／`polarity`** | pass 1 即可看 |
| `pass1-sheet-qiu-zhenhao.csv` | 邱振豪的独立判定表：seq／组／case_id／类别／v0.1.1 条款指针 ＋ 空白 `adj_*`／`basis`／`pass1_done`；**无 A／B 判定、无分歧门、无草案** | 仅本人 pass 1 填写 |
| `pass1-sheet-yang-bingbing.csv` | 杨冰冰的独立判定表，列同上 | 仅本人 pass 1 填写 |
| `adjudication-sheet.csv` | pass 2 对齐表（54 行 × 36 列）：A／B 六字段判定与 note、`gate_A`／`gate_B`、分歧类型、条款指针；`adj_*` 填**对齐后的共识值** | pass 2 |
| `draft-reference.csv` | 草案 `expected` 与作者 `notes` | **只在 pass 3 打开** |
| `build-pack.py` | 生成脚本（争议集、分组、门映射、裁决人名单都在这里） | 随时 |

> pass 1 的两份表**互不共享**：先把两份都交回，才进入 pass 2；不得先看对方的 `adj_*`。

## 分组（按优先级，顺序即行序）

| 组 | n | 内容 | 适用 v0.1.1 条款 |
|---|---:|---|---|
| **P0** | 3 | 硬约束 decision 级：TEN-015（A/B 分歧）、TEN-016（双标一致但漏看 `session_owner_id`）、TIME-016（G8 部分放行） | G1 清单第 1–2 项；G8 副作用落点 |
| **P1** | 3 | 澄清 vs 拒绝：COR-012、CTRL-011、TIME-020（双标一致判 `REJECT`，草案 `NEEDS_CLARIFICATION`） | §四“澄清还是拒绝”情形 3–4 |
| **P2** | 23 | 字段口径：`subject_ok`／`time_ok`／`sensitivity_action` 的 A/B 分歧与“双标一致偏离草案” | §3.2 字段判据（正交性、读取类 `subject_ok`、`unclear` 条件） |
| **P3** | 25 | 取码：`primary_reason`／`operation` 分歧与偏离草案 | 主理由选择规则 1–6（含 G7 内部顺序） |
| 合计 | **54** | A/B 分歧 37 条 ∪ 双标一致偏离草案 22 条（有重叠） | — |

**硬约束优先**：P0 三条必须两人一致裁完并复核，才谈 P1–P3；P0 未闭合前不进入模型评分。

## 流程（三遍，rubric §6.4 防对答案）

**pass 1 · 各自独立裁决（不看 A／B 判定，不看 `draft-reference.csv`）**
1. 两人都读规则 v0.1 ＋ rubric **v0.1.1**（重点：§四“澄清还是拒绝”、G1 逐字段清单、G8 落点、主理由选择规则、§3.2 字段判据）。
2. 只用 `adjudication-material.jsonl` 的输入字段 ＋ 本人那份 `pass1-sheet-*.csv` 的条款指针，独立填六个 `adj_*` 字段与 `basis`，勾 `pass1_done`。
3. 条款指针是**定位工具不是答案**；两人都交回后才进 pass 2。

**pass 2 · 对齐（打开 `adjudication-sheet.csv`，仍不看草案）**
1. 并列比对两份 `pass1` 值：一致 → 抄入 `adj_*` 作为共识；`gate_A`／`gate_B` 是 A／B 各自主理由所落的门（自动映射，可订正）。
2. 不一致 → 按 v0.1.1 条款讨论；**仍不一致则写 `basis=UNRESOLVED: <两值>＋理由`，不得任一方单方定案**。
3. **P0 三条必须两人一致才闭合**；P0 未闭合 → 硬约束仍判未过，暂停模型评分。
4. `adjudicator` 已预填“邱振豪＋杨冰冰（独立 pass 1 后对齐）”。

**pass 3 · 对草案（才打开 `draft-reference.csv`）**
1. 比较共识值与草案 `expected`；不一致写 `change_expected=YES: <字段> <草案>→<共识>` 或 `NO: <理由>`；同时判断是否改用例（`change_case`）或再改 rubric（`change_rubric`）。
2. 改 `cases/*.jsonl` 的 `expected` 必须两人共同确认并升版本，且**不回改 A／B 原始 CSV**。

## 完成判据

- 两份 `pass1-sheet-*.csv`：54 行 `adj_*` 全非空、`pass1_done=YES`；
- `adjudication-sheet.csv`：54 行 `adj_*`／`basis` 全非空，`UNRESOLVED` 计数为 0（尤其 P0 三条必须一致）；`pass2_done`（对齐完成）与 `pass3_done`（对草案完成）全 `YES`，`change_*` 已回填；
- 结果回填 `annotation-status.md` §四（逐行裁决结果与依据）与 §3.3 三张表；
- 复评：保留两份原始 CSV，另存裁决后标签重跑 `python3 validate.py --score`，确认硬约束 `decision` 100% 一致、六字段仍过门槛；
- 只有全部达标后，才把 `cases/*.jsonl` 的 `expected` 升级为 v0.2 人工金标（改标签须同时升 `manifest.json` 的 `version`／`label_status` 并在 §五 记录改了哪几条）。

## 边界

- 本目录只是流程与数据组织，**不构成裁决结论**：`rubric_v0.1.1_clause` 是指针，最终值必须两裁决人签字。
- **杨冰冰（标注者 A）与邱振豪（规则作者）都不得单独定案**；两人 pass 1 必须先独立、后对齐，对不齐就标 `UNRESOLVED`，不得“讨论到一方让步”。
- 邱振豪在 pass 3 前不得以“我是作者”为由引用 `expected`／`notes`；草案被推翻要走升版本流程，不静默改标签。
- 季星辰（B）不参与裁决，也不得在 pass 1／2 中提供倾向性意见；其原始 `note` 已在对齐表中，属证据而非裁决。
- 不得用“多数投票”抹平分歧，不得删除不一致样本（rubric §6.2）。
