# AgeGuard 记忆字段与写入规则 v0.1

> 状态：**规则草案**。用于实现与合成评测的前置契约，不是已上线服务、数据库迁移或已通过人工复核的标准。
> 范围：个人长期记忆的候选、审查、提交、修订、删除抑制与读取门禁。
> 不覆盖：提醒调度、家庭授权、求助状态机、医学判断。它们与记忆是不同领域，记忆写入不得顺带改变这些对象。
> 配套：[标注 rubric](annotation-rubric-v0.1.md)｜[合成用例集说明](README.md)｜需求与选型背景见 AgeGuard 主仓库 `research/记忆门禁-功能需求与开源选型.md`（不复制外部文档）

## 一、设计原则

1. **先候选、后有效**：抽取结果只是候选，不能直接成为长期记忆；只有门禁批准且事务提交后才生效。
2. **证据先于事实**：记忆保存“谁在什么时间说了什么”，不证明现实世界必然为真。本人自述、转述、未确定必须分开。
3. **程序管硬约束，模型管语义建议**：身份、来源、权限、schema、版本、幂等、事务、删除抑制、派生传播由程序负责；模型只能提出候选、理由和证据引用。
4. **宁可待澄清，不默认通过**：评审失败、超时、来源缺失、时间不明、敏感内容，都不能按“看起来没问题”提交。
5. **修订不是覆盖历史**：显式更正生成新版本，旧版保留最小证据并退出当前召回；删除、取消、撤销、不分享是不同操作。
6. **记忆不越权**：私人记忆默认只属于本人；绑定亲属不等于获得私人记忆读取权；家庭侧只读授权投影。
7. **可删除、可解释、可重放测试**：每次提交有决策、理由码、规则／提示词／模型版本、来源与版本；固定用例可重复判定。

## 二、术语

| 术语 | 含义 |
|---|---|
| 来源（source） | 获准处理的最终转写或用户操作，至少含 owner、说话者、会话、轮次、修订、时间与文本。临时转写不是来源。 |
| 表达时间（`expressed_at`） | 用户说出这句话的时间，不等于事实发生或适用的时间。 |
| 适用时间（`valid_from` / `valid_to`） | 该命题在世界上被断言适用的区间；`null` 表示在证据范围内未给出终点，不等于永久为真。 |
| 记录时间（`recorded_at`） | 服务端提交该版本的时间。 |
| 状态（status） | 候选状态与记忆生命周期状态分开，见第四节。 |
| 修订关系 | 新版本与旧版本之间的替代、保留、证据链接与失效关系。 |
| 删除抑制 | 为阻止旧任务、备份恢复或派生内容复生而保留的最小标记；不是无限保存敏感原文。 |
| 正例／反例 | 用例集中：正例是边界条件应被正确满足并允许写入／读取；反例是边界违规应被拒绝、澄清或延迟。见 [README](README.md)。 |

## 三、字段

### 3.1 身份与来源

| 字段 | 类型 | 必填 | 由谁决定 | 说明 |
|---|---|---:|---|---|
| `candidate_id` | string | 是 | 服务端 | 候选随机 ID，不复用。 |
| `owner_id` | string | 是 | 服务端（认证／会话） | 记忆所属本人。模型不得填写或改写。 |
| `speaker_id` | string | 是 | 来源 | 这句话是谁说的；与 `owner_id` 可不同。 |
| `session_id` | string | 是 | 来源 | 会话 ID。 |
| `turn_id` | string | 是 | 来源 | 最终轮次 ID。 |
| `source_revision` | int | 是 | 来源 | 转写修订号；旧修订不能覆盖新修订。 |
| `source_final` | bool | 是 | 来源 | 仅 `true` 可作为正式写入来源。 |
| `evidence_refs` | array | 是 | 抽取＋服务端校验 | 指向来源片段／字符范围／操作记录；不能只有模型转述。 |
| `source_text` | string | 是 | 来源 | 获准保留的原话片段；不得把模型补全写进来。 |
| `source_timezone` | IANA string | 是 | 服务端 | 解析相对日期用；默认 `Asia/Shanghai`，但必须显式记录。 |
| `source_owner_id` | string | 是 | 服务端 | 来源归属；用于检测会话／账号错配。 |

### 3.2 语义与主体

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `memory_type` | enum | 是 | `background`／`preference`／`habit`／`relation`／`ongoing_event`／`health_note`／`plan_context`。计划本身另属提醒领域。 |
| `subject_kind` | enum | 是 | `self`／`family_member`／`other_person`／`pet_or_object`／`event`。 |
| `subject_id` | string | 是 | 主体 ID 或稳定的关系标签；不能只写“她”“他”。 |
| `claim` | string | 是 | 可独立修订的原子命题；保留否定、条件、数量、例外、不确定性和关系背景。 |
| `assertion_status` | enum | 是 | `self_report`（本人自述）／`reported_other`（转述他人）／`uncertain`（本人未确定）／`user_confirmed`（本人对候选明确确认）。 |
| `negation` | object | 否 | 结构化保留：`present`、作用域、例外；文本 `claim` 仍须可读。 |
| `quantifier` | string | 否 | `all`／`some`／`daily`／`weekly`／`once` 等；禁止把“有时”扩成“总是”。 |
| `condition` | string | 否 | “下雨就不去”“只在这周”等条件。 |
| `sensitivity` | enum | 是 | `normal`／`personal`／`health`／`financial`／`family_private`／`restricted`。健康与财务默认更谨慎。 |
| `scope` | enum | 是 | `private`（默认）／`family_projection`（仅授权投影，不是私人记忆读取权）。 |
| `retention_policy_id` | string | 是 | 例如 `default_background`／`transient_state`／`limited_health_note`／`sensitive_review`。 |

### 3.3 时间

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `expressed_at` | timestamptz | 是 | 原话表达时间。 |
| `valid_from` | timestamptz／null | 是 | 适用起点；无法确定则为 `null` 并触发澄清或仅存带不确定性的候选。 |
| `valid_to` | timestamptz／null | 是 | 适用终点；临时状态必须有终点或明确保留期限。 |
| `time_precision` | enum | 是 | `instant`／`hour`／`day`／`week`／`month`／`year`／`life_stage`／`unknown`。 |
| `time_label` | string／null | 否 | 保留“年轻时”“最近”“这几天”等原始时间表达，避免解析后丢失语义。 |
| `recurrence` | string／null | 否 | `daily`／`weekly`／`monthly`／`yearly` 等；仅表示陈述，不自动生成提醒。 |
| `expires_at` | timestamptz／null | 否 | 记录层保留期限；到期后退出当前召回。 |
| `recorded_at` | timestamptz | 是 | 服务端记录时间。 |

**规则**：`expressed_at`、`valid_from`、`valid_to`、`recorded_at` 不可混用。“今天不出门”不能写成“长期不爱出门”；“上周摔了一跤”不能写成“现在腿脚不好”。

### 3.4 变更与版本

| 字段 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| `operation` | enum | 是 | 建议操作：`ADD`／`NOOP`／`MERGE`／`REVISE`。删除与到期不由模型直接执行。 |
| `target_memory_id` | string／null | 条件 | `REVISE`／`MERGE` 必填。 |
| `expected_version` | int／null | 条件 | 乐观并发；`REVISE` 必填。 |
| `memory_group_id` | string | 是 | 跨版本稳定的逻辑组 ID。 |
| `version` | int | 是 | 版本号从 1 开始，单调递增。 |
| `supersedes` | array | 否 | 被本版本替代的旧版本 ID。 |
| `superseded_by` | string／null | 否 | 旧版本指向新版本。 |
| `revision_reason` | enum／null | 条件 | `explicit_correction`／`change_over_time`／`merge_dedupe`／`error_fix`。 |
| `candidate_hash` | string | 是 | 绑定候选内容与版本；评审后改写候选则原批准失效。 |
| `idempotency_key` | string | 是 | 服务端生成；同一逻辑操作只提交一次。 |
| `policy_version` | string | 是 | 本次使用的规则／保留策略版本。 |
| `reviewer_version` | string | 是 | 审查提示词／模型／规则版本。 |

### 3.5 决策与审计

| 字段 | 类型 | 说明 |
|---|---|---|
| `decision` | enum | `APPROVE`／`REJECT`／`NEEDS_CLARIFICATION`／`DEFER`。 |
| `reason_codes` | array | 必填，至少一个；使用第七节封闭词表。 |
| `review_evidence` | array | 支持决策的原话、旧版本、diff 或删除标记引用。 |
| `reviewed_at` | timestamptz | 审查时间。 |
| `committed_at` | timestamptz／null | 事务提交时间；未提交不得对外说“已记住”。 |
| `commit_receipt` | object／null | 业务回执；重复提交返回原回执。 |
| `deletion_state` | object | `active`／`deleted`／`suppressed`；与候选、记忆、索引、摘要分开记录。 |

## 四、状态机

### 4.1 候选状态

```text
DRAFT
  → PENDING_REVIEW
      → APPROVED_PENDING_COMMIT → COMMITTED
      → REJECTED
      → NEEDS_CLARIFICATION → (补充来源／确认后重新审查)
      → DEFERRED → (条件满足后重新审查或过期清理)
      → SUPERSEDED（被新候选／新来源改口替代）
      → EXPIRED（隔离区到期）
```

- `APPROVED_PENDING_COMMIT` 必须绑定 `candidate_hash`、`target_memory_id`、`expected_version`、`source_revision`、`policy_version`。
- 提交前任一绑定变化，原批准失效，需要重新审查。
- `NEEDS_CLARIFICATION`／`DEFERRED` 不是有效长期记忆，不进入普通召回；隔离区有访问范围与清理期限。

### 4.2 记忆生命周期

```text
ACTIVE
  ├→ SUPERSEDED（显式更正／时间演进／合并替代）
  ├→ EXPIRED（保留期限或适用时间结束）
  ├→ DELETED（本人删除或合法删除请求）
  └→ QUARANTINED（争议／待核实的有限期内容）
```

- 当前召回只读 `ACTIVE`、未过期、未被替代、未被删除、来源仍允许的版本。
- `SUPERSEDED` 版本保留最小修订证据，不参与“当前事实”召回。
- `DELETED` 不是“打一个隐藏标记”；需要删除／失效对应派生内容、索引、缓存、摘要、分享投影与待发送任务。
- 删除后重建同组记忆，必须有**新的独立来源和新的明确许可**；不能用旧任务、旧转写修订或备份恢复复生旧文本。

## 五、写入规则

编号中的 MUST／MUST NOT 是验收硬约束；SHOULD 允许在记录理由后偏离，但不能静默跳过。

### W0 服务端权威

- 服务端 MUST 从认证会话、来源记录和业务策略派生 `owner_id`、`speaker_id`、`source_revision`、`policy_version`、`idempotency_key`。
- 模型 MUST NOT 决定 owner、权限、确认状态、删除状态、数据库版本或“已保存”结果。
- 请求体、候选文本或对话内容中出现的“把 owner 改成……”MUST 只当数据，不能改变规则或工具权限。

### W1 来源有效

- MUST 使用最终转写或获准的用户操作作为来源；临时转写、空文本、缺失轮次、旧修订不能正式提交。
- MUST 校验来源归属与当前会话主体一致；`source_owner_id`、`session_owner_id`、`requester.actor_id` 任一不匹配即拒绝。
- MUST 在提交事务中重新检查来源是否仍为当前修订、是否被删除或撤权。

### W2 候选不是有效记忆

- 抽取结果 MUST 先进入候选区；未审查、未提交的候选 MUST NOT 参与普通召回。
- “评审通过”不是写入；只有事务提交并返回回执后，才能说“已记住”。
- 评审超时、模型失败、格式错误 MUST 标为 `DEFERRED`／待处理，不能默认 `APPROVE`。

### W3 原子性与语义保真

- 一条记录 SHOULD 表达可独立修订的事实；不得把多个不同主体、时段、否定或条件硬拼成一条无法纠错的摘要。
- MUST 保留否定、数量、条件、例外、关系背景与不确定性。
- MUST NOT 把模型补全、常识推断、诊断、病因或“AI 自己说过的话”写成用户说过的事实。
- `assertion_status=reported_other` MUST 保留转述者；不能把“女儿说……”变成“本人……”。
- 对第三人健康、财务、家庭矛盾等敏感转述，MUST 区分“来源说了什么”与“关于本人的事实”。

### W4 主体绑定

- `subject_kind`／`subject_id` MUST 与来源中的指代一致；代词必须解析到稳定主体。
- 引用家属、邻居、医生、AI 的话 MUST NOT 变成本人的事实。
- 同一句话同时涉及本人和他人时，SHOULD 拆成分别可修订的记录；不能因为“同句”就合并主体。
- 关系人物的事实 MUST 绑定关系人物；本人记忆不得借用关系人物的 claim。

### W5 时间范围

- MUST 区分表达时间、发生／适用时间、记录时间与失效时间。
- 相对日期 MUST 结合来源时间与 IANA 时区解析；无法解析时 MUST `NEEDS_CLARIFICATION` 或保存为 `uncertain`，不能猜一个精确日期。
- 临时状态（“今天”“这几天”“这次”）MUST 有 `valid_to` 或明确保留期限；不得写成永久特征。
- 过去经历 MUST NOT 写成当前状态；当前状态 MUST NOT 覆盖历史版本而不保留时间分段。
- 习惯／周期陈述 MUST 保留 recurrence 语义，但 MUST NOT 自动创建或修改提醒计划。
- 时间范围重叠且无法裁决时，MUST `NEEDS_CLARIFICATION`；不能任选一个“看起来更合理”的版本。

### W6 否定与量词

- MUST 保留否定作用域与例外；“不吃海鲜，但鱼可以”不能写成“不吃鱼”或“不吃海鲜”。
- MUST NOT 把“不是每天”扩成“每天”，把“有时”扩成“总是”，把“不太会”强化成“完全不会”。
- 双重否定、反问、假设、引用他人否定 MUST 先解析语义，不能按关键词匹配直接反转。
- 候选丢失或增加否定时，MUST `REJECT`（除非是来源明确支持的新更正，按 W8 处理）。

### W7 去重与增量

- 完全重复或语义等价且主体、时间、否定、条件一致时，SHOULD `NOOP` 并追加证据链接，不新增第二条有效记忆。
- 相似但主体、时段、否定、条件或不确定性不同者 MUST NOT 合并；应分别 `ADD`／`REVISE` 或待澄清。
- 相似度分数不是事实；不得仅凭 embedding 相似度覆盖旧记录。
- 合并（`MERGE`）MUST 保留所有关键旧信息与来源；合并前后信息损失即拒绝。

### W8 冲突、改口与修订

- 明确更正（“不是小颗粒，是薄片”“我说错了”）MUST 生成新版本，`operation=REVISE`，旧版 `SUPERSEDED`，`revision_reason=explicit_correction`。
- 随时间改变（“以前……现在……”）MUST 保留时间分段；可修订当前版本或新增带区间的版本，但不能抹掉过去。
- 不同情境并存（“在家吃辣，外面不吃”）MUST 保留条件，不得粗暴合并成矛盾摘要。
- 真正矛盾且来源无法裁决时，MUST `NEEDS_CLARIFICATION`；不能由模型自行选一个版本。
- 改口只影响相关记忆；MUST NOT 顺带修改提醒、授权、分享、求助或家庭设置。
- 评审后候选内容或目标版本变化，原批准 MUST 失效；并发冲突后 MUST 重新读取、重新审查。

### W9 敏感内容与保留

- `sensitivity=health`／`financial`／`family_private` 的候选 MUST 走更谨慎规则；本版 MVP 不把敏感健康内容纳入自动长期记忆。
- 敏感内容可以在本人明确要求、范围清楚、保留期限有限时保存为私人事件候选；MUST 保留“本人自述／未确定”，不得写诊断、病因、用药调整或风险评分。
- 含糊或敏感内容 MUST NOT 直接固化为确定事实；应 `NEEDS_CLARIFICATION` 或 `DEFER`，并说明需要本人确认什么。
- “别记”MUST 阻止该来源派生持久记忆，并清理候选／原文的可清理部分；“别告诉孩子”只限制分享，不等于删除本人私人记忆；“不分享”不等于删除私人记忆。
- 敏感内容的分享 MUST 走独立授权；记忆写入不得生成家庭投影、通知或“有秘密内容”的旁路提示。

### W10 删除与重处理

- 提交前 MUST 检查候选来源、目标记忆、证据链是否命中删除抑制；命中即拒绝。
- 删除后旧任务重试、旧转写修订、旧候选、索引重建、摘要再生成、备份恢复 MUST NOT 复生已删除内容。
- 删除抑制 MUST 记录对象、来源、范围与时间；MUST NOT 为防复生无限保存敏感原文。
- 本人以后以**新的独立来源**明确要求重新记录的新信息，不受旧文本黑名单永久阻止；但必须按新候选重新审查，不能把旧删除内容直接恢复。
- 删除 MUST 传播到候选、有效记忆、摘要、索引、缓存、分享投影与未发送任务；数据库与异构索引不假设天然原子提交。

### W11 跨用户隔离

- 所有读取与写入 MUST 同时校验认证主体、`owner_id`、目标记忆归属和用途。
- 模型传入的 owner／recipient MUST NOT 决定权限；服务端 MUST 从认证与会话解析。
- 亲属绑定 MUST NOT 授予私人记忆读取权；家庭侧只读授权投影，不提供“先读全量再过滤输出”的路径。
- 跨用户写入、跨租户读取、伪造 owner、撤销后的 grant MUST 拒绝；拒绝理由不得向无权方泄露对方内容。
- 至少用两个测试家庭验证隔离；同一家庭内也要区分本人／亲属／其他亲属。

### W12 幂等、版本与事务

- 每个逻辑变更 MUST 有唯一幂等键；同一键重复提交 MUST 返回原回执，不新增第二条记忆。
- `REVISE`／`MERGE` MUST 带 `expected_version`；版本冲突 MUST 返回冲突并重新审查，不能用旧决策强行覆盖。
- 提交事务 MUST 复核：来源当前、策略当前、候选 hash 与评审一致、目标版本一致、删除抑制未命中。
- 唯一约束是最终防线；冲突后不能无限重试旧批准。

### W13 副作用分离

- 记忆提交 MUST NOT 创建／修改提醒、授权、分享、求助、通知或家庭设置。
- 从“每周六通常换水”只能得到习惯记忆；不能自动启用周期提醒。
- 从“请女儿带鱼粮”得到的是求助候选，不是记忆或分享授权。
- 记忆修订 MUST NOT 自动改写已分享的旧投影或已确认的请求；需要新的确认与授权。

### W14 读取门禁与召回

- 普通召回 MUST 只读当前用户或请求者获准对象；过滤 `DELETED`／`EXPIRED`／`SUPERSEDED`／`QUARANTINED`。
- 返回结果 MUST 带来源、版本与适用时间；索引旧结果 MUST 按权威记录复核状态。
- 召回失败 MUST 如实说“暂时查不到”，不能编造记得；依赖该记忆的高影响动作应暂停核对。
- 家庭侧生成上下文 MUST 先按授权取数，再生成；不得把私人记忆交给模型后靠输出过滤。

### W15 可观测与故障

- MUST 记录候选、决策、理由码、提交回执、规则／提示词／模型版本、延迟、token 与费用。
- 评审失败、提交失败、通知未知 MUST 状态分开；不能把“已受理”当“已展示”，也不能把“待处理”说成“已记住”。
- 固定用例中的越权、删除复生、非法改计划 MUST 全部通过；一次通过不等于生产永久安全。

### W16 价值与保留判断

- 低价值、无长期用途的瞬时信息（“刚才把杯子放到桌上”“今天阳光真好”）默认 `NOOP`；不要为演示或覆盖率强行记忆每一句。
- 本人明确要求记着、或对未来交流／安排／家庭回忆有用时，才进入长期记忆候选。
- “低价值”不是删除已存在记忆的理由；保留期限、过期与重要性排序按策略处理。

### 风险分级与确认表（摘要）

| 级别 | 典型内容 | 默认处理 | 确认要求 |
|---|---|---|---|
| R0 普通生活背景 | 养鱼、听戏、日常习惯、普通偏好 | 可在保存许可开启时后台写入；显示可撤销结果 | 不要求每句点确认 |
| R1 个人隐私 | 财务紧张、家庭关系、不想让某亲属知道 | 默认私人；不分享；可设有限期限 | 本人明确要求保存；分享另行授权 |
| R2 敏感健康 | 血压／睡眠／起夜／记性／用药／诊断 | 不纳入自动长期记忆；只允许本人明确、私人、有限期的自述记录 | 需要本人确认范围与期限；禁止诊断／用药／风险推断 |
| R3 高影响副作用 | 提醒、分享、求助、通知、授权 | 记忆不得代办；必须走独立领域与卡片确认 | 绑定动作、对象、内容、版本与有效期 |
| R4 删除／撤权 | 删除记忆、撤销分享、解除绑定 | 立即生效并传播到派生内容；旧任务不得复生 | 本人明确操作；不要求模型同意 |
| R5 跨用户／权限 | 他人记忆、亲属私人读取、伪造 owner | 服务端拒绝；不向无权方泄露内容 | 认证与业务授权，不由模型判断 |

“嗯”“行吧”等泛化附和不能完成 R3 的高影响确认；确认必须绑定具体动作、对象、内容版本与有效期。

## 六、决策优先级

**决策与操作分开**：`APPROVE` 不等于写入；`APPROVE`＋`NOOP` 表示“允许这条候选存在，但不新增／不改写”（等价重复、低价值瞬时、纯闲聊无记忆意图）。只有 `ADD`／`MERGE`／`REVISE` 才产生新版本。

按顺序执行；前一步拒绝后不再用后一步“救回”。

| 顺序 | 门 | 典型结果 |
|---:|---|---|
| 1 | 身份／来源完整性 | 来源缺失、临时转写、会话错配 → `REJECT` |
| 2 | 跨用户／权限 | 跨租户、伪造 owner、无授权家庭读取 → `REJECT` |
| 3 | 删除抑制 | 已删除来源／目标、旧任务重放、备份复生 → `REJECT` |
| 4 | 主体绑定 | 转述他人写成本人、指代不明 → `REJECT`／`NEEDS_CLARIFICATION` |
| 5 | 语义保真 | 否定丢失、数量扩大、诊断推断、AI 事实 → `REJECT` |
| 6 | 时间范围 | 范围不明 → `NEEDS_CLARIFICATION`；临时写成永久 → `REJECT` |
| 7 | 去重／冲突／修订 | 等价重复 → `NOOP`；明确更正 → `REVISE`；无法裁决 → `NEEDS_CLARIFICATION` |
| 8 | 敏感／保留 | 敏感自动长期化 → `DEFER`；明确有限私人记录 → `APPROVE`（限保留） |
| 9 | 副作用 | 试图改提醒／授权／分享 → 拒绝副作用；必要时只允许纯记忆部分 |
| 10 | 无违规 | `APPROVE` ＋ `ADD`／`NOOP`／`MERGE`／`REVISE` |

**默认值不是 APPROVE。** 任一门无法完成检查时，结果为 `DEFERRED`／`NEEDS_CLARIFICATION`，并记录原因。

**硬拒绝优先于澄清／延迟。** 同一候选同时触发“待澄清／延迟”和后面的硬拒绝（跨用户、删除、错人写成自己、否定反转、诊断／用药／风险推断）时，按硬拒绝处理；不要因为“可以再问本人”就放行一个本应拒绝的候选。反过来，只有澄清能解决的歧义不能强行 APPROVE。

## 七、理由码封闭词表 v0.1

> 用例集只使用下列主理由码；新增码必须先改本表并升版本。

### 来源与身份
`SOURCE_MISSING`、`SOURCE_NOT_FINAL`、`SOURCE_STALE_REVISION`、`SESSION_OWNER_MISMATCH`、`OWNER_MISMATCH`、`MODEL_SET_OWNER`

### 否定与语义
`NEGATION_PRESERVED`、`NEGATION_LOST`、`NEGATION_INVERTED`、`NEGATION_STRENGTHENED`、`NEGATION_SCOPE_SHIFT`、`QUANTIFIER_EXPANDED`、`EXCEPTION_DROPPED`、`RELATION_MISREAD`

### 主体
`SUBJECT_BOUND`、`SUBJECT_MISMATCH`、`QUOTED_OTHER_AS_SELF`、`THIRD_PARTY_AS_SELF`、`REPORTED_ABOUT_SELF_NEEDS_CONFIRMATION`

### 时间
`TIME_SCOPE_BOUNDED`、`TIME_SCOPE_PRESERVED`、`TIME_SCOPE_EXPANDED`、`TIME_ANCHOR_WRONG`、`TIME_ANCHOR_AMBIGUOUS`、`PAST_AS_CURRENT`、`ONE_OFF_AS_HABIT`、`ONE_OFF_AS_RECURRING`、`RECENT_AS_PERMANENT`、`TRANSIENT_AS_PERMANENT`、`RECURRENCE_PRESERVED`

### 去重、改口与冲突
`DUPLICATE_NOOP`、`EXPLICIT_CORRECTION`、`EXPLICIT_CHANGE`、`CHANGE_OVER_TIME`、`NOT_EXPLICIT_CORRECTION`、`UNCERTAIN_CORRECTION`、`REPORTED_CHANGE_NEEDS_CONFIRMATION`、`UNCERTAIN_RESCHEDULE`、`CONFLICT_UNRESOLVED`、`CONTEXT_AS_CORRECTION`

### 敏感与保留
`PRIVATE_ONLY`、`SENSITIVE_PRIVATE_ALLOWED`、`SENSITIVE_LIMITED_RETENTION`、`SENSITIVE_REQUIRES_CONFIRMATION`、`DIAGNOSIS_INFERENCE`、`MEDICATION_INFERENCE`、`RISK_INFERENCE`、`ASSISTANT_FACT_NOT_SOURCE`、`REPORTED_MEDICAL_CLAIM`、`SHARE_WITHOUT_GRANT`

### 删除与派生
`NEW_SOURCE_AFTER_DELETE`、`EXPLICIT_REAUTHORIZATION`、`DELETED_SOURCE_REPLAY`、`DELETED_SOURCE_REVISION`、`DELETED_TARGET`、`DELETED_MEMORY_RECALL`、`RESTORE_RESURRECTION`、`DERIVED_CONTENT_RECOVERY`、`DELETED_MEMORY_SHARE`、`SUPPRESSION_HIT`

### 隔离与权限
`OWNER_MATCH`、`CROSS_TENANT_WRITE`、`CROSS_TENANT_READ`、`TARGET_OWNER_MISMATCH`、`FAMILY_WRITE_DENIED`、`FAMILY_PRIVATE_READ_DENIED`、`PRIVATE_MEMORY_NOT_GRANTABLE`、`GRANT_REVOKED`、`FORGED_OWNER`

### 副作用与其他
`SIDE_EFFECT_BLOCKED`、`MEMORY_AS_REMINDER`、`RECURRENCE_AS_PLAN`、`NO_MEMORY_INTENT`、`LOW_VALUE_TRANSIENT`、`UNCERTAINTY_NOT_RESOLVED`、`SCHEMA_INVALID`、`REVIEW_FAILED`

## 八、项目必测例子

| 输入／事件 | 规则结果 |
|---|---|
| “今天不想出门。” | 至多记录当天／有限期状态，不生成永久性格画像。 |
| “不是小颗粒，现在换薄片了。” | 显式修订相关鱼粮记录；旧版退出当前召回。 |
| “以前爱吃甜的，现在控制一下。” | 保留过去偏好与当前意愿的时间分段，不拼成矛盾摘要。 |
| “我女儿不吃辣。” | 记关系人物的陈述，不能写成老人本人不吃辣。 |
| “我邻居说她最近胃痛。” | 记“邻居说她胃痛”的转述；不创建老人胃痛事实。 |
| “我前几天肚子疼，好像吃坏了。” | 若获准保留，记本人自述＋不确定性＋有限期；不写诊断或病因。 |
| “每周六通常换水。” | 可记带来源的习惯；不自动启用周期提醒。 |
| “这件事别记，也别告诉孩子。” | 不长期保留该来源派生记忆；不共享；不发旁路提示。 |
| “记着就行，不要告诉女儿。” | 可在有效保留设置下留私人记忆；没有分享许可。 |
| 同一轮次重试三次 | 只产生一次逻辑变更；重复返回原回执。 |
| 删掉后旧后台任务迟到／重放 | 被删除抑制拦截，不重新写回。 |
| AI 自己说“她已经康复了” | 不作为老人康复的事实来源。 |

## 九、最小 schema 草案

以下是字段契约示意，不是现有 ORM 表定义：

```python
class SourceRef(BaseModel):
    owner_id: str
    speaker_id: str
    session_id: str
    turn_id: str
    source_revision: int
    source_final: bool
    expressed_at: datetime
    timezone: str
    text: str

class Candidate(BaseModel):
    candidate_id: str
    source: SourceRef
    memory_type: Literal["background", "preference", "habit", "relation",
                         "ongoing_event", "health_note", "plan_context"]
    subject_kind: Literal["self", "family_member", "other_person",
                          "pet_or_object", "event"]
    subject_id: str
    claim: str
    assertion_status: Literal["self_report", "reported_other",
                              "uncertain", "user_confirmed"]
    expressed_at: datetime
    valid_from: datetime | None
    valid_to: datetime | None
    time_precision: Literal["instant", "hour", "day", "week", "month",
                            "year", "life_stage", "unknown"]
    time_label: str | None = None
    recurrence: str | None = None
    operation: Literal["ADD", "NOOP", "MERGE", "REVISE"]
    target_memory_id: str | None = None
    expected_version: int | None = None
    memory_group_id: str
    sensitivity: Literal["normal", "personal", "health", "financial",
                         "family_private", "restricted"]
    scope: Literal["private", "family_projection"]
    retention_policy_id: str
    candidate_hash: str
    idempotency_key: str
    policy_version: str
    reviewer_version: str

class ReviewResult(BaseModel):
    decision: Literal["APPROVE", "REJECT", "NEEDS_CLARIFICATION", "DEFER"]
    operation: Literal["ADD", "NOOP", "MERGE", "REVISE"]
    reason_codes: list[str]  # 至少 1 个；来自封闭词表
    review_evidence: list[str]
    reviewed_at: datetime
```

## 十、已知边界与未完成项

- 本规则是 **v0.1 草案**，未在真实数据库、并发 worker、删除传播、备份恢复或真实模型上验证。
- 用例集为合成数据，标签为助手起草的**草案标签**；尚未完成第二人独立人工标注，不能声称“人工标注已完成”或“一致性已达标”。标注协议见 [rubric](annotation-rubric-v0.1.md)。
- 用例是候选级，不是完整对话级：没有多轮改口、跨会话事件序列、ASR 噪声或说话人切换；这些需另建序列用例。
- `MERGE` 只有规则定义，v0.1 没有正向合并用例；合并前后信息损失与关键旧信息保留需下一版补测。
- 中文分词、全文检索、向量召回、模型结构化输出能力需按实际部署验证；本规则不假设某个 RDS／模型天然支持。
- 敏感健康的“有限期私人记录”仍需产品与合规复核；本规则只给出技术门禁，不是医疗或法律结论。
- 删除抑制的“最小标记”与“本人重新明确允许”的边界需在真实删除／恢复实验中验证；合成用例只覆盖契约层。
- 本规则不能承诺数学意义的“不劣化”；只能要求硬约束通过、变更可追溯、错误可纠正，并在固定测试集上报告结果。
