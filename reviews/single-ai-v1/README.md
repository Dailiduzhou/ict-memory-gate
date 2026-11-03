# 单AI复核标注结果

本批155条已完成单AI非盲复核，27条提出标签修改，32条包含规则/输入完善建议。未改动原cases或expected；annotations.jsonl保存草案、复核标签、差异字段与证据。

这是同一聊天中看过草案后的复核，不是独立盲标，不是人工金标，也不是模型准确率测试。保留标签在草案基础上复核，不能拿与草案的相同比例当正确率；没有两名标注者，不计算κ或双人一致率。

## 使用

运行 `python3 audit_ai_review.py` 校验覆盖、枚举、引用、哈希、差异和返回ID。标签是PR建议版本；训练/最终测试金标应另经人工裁决。现有155条的正反例比例属于原草案，不代表复核标签继续保持10正10反。

## 建议规则（仅适用于复核建议，不静默改原规格）

1. G7：拒绝分享不自动授权保存，敏感保存须明确意愿或输入给出有效预授权；候选自身的scope/retention_policy_id不是用户同意证据。
2. G2：相关主题删除后，新来源不等于重新授权；删除范围不明先澄清，不能依notes猜测无关。CONFLICT_UNRESOLVED暂作缺许可的理由，下一版可增专用码。
3. G5：不得虚构精确时刻；周界定明确为周一开始，周范围不代表实际入住起点。明确时间扩大应拒绝当前候选，来源本身可能仍可另行澄清。
4. valid_to为事实适用区间，不是保留期限；保留建议增加独立retention_until与授权/策略证据。这里仅标记问题，不大规模改写输入。
5. self_report建议统一解释为“来源说话者本人提供的信息”，about-self转述仍要保留reported_other，不按主语是否老人简单判断；当前相关命名需团队确认。

## 修改与输入问题清单

| 用例 | 原决定→建议决定 | 差异字段 | 理由 |
|---|---|---|---|
| COR-007 | APPROVE → NEEDS_CLARIFICATION | decision, operation, primary_reason, time_ok | G5：只给下午/改到周四，未给14:00—17:00；已有记忆若支持沿用时间需提供来源。候选时间精度超过证据，应保留模糊时段或确认具体时刻。 |
| COR-010 | APPROVE → NEEDS_CLARIFICATION | decision, operation, primary_reason, time_ok | G5：当前年级不能证明9月1日开始；起点建议用表达时间/未知，或补充来源，不能自动当作入学日期。 |
| COR-012 | NEEDS_CLARIFICATION → REJECT | decision | G5已明确本周一次变化，候选扩成以后每周；按硬拒绝优先规则拒绝当前候选，另可提出正确候选，不以澄清救回错误候选。 |
| TIME-002 | APPROVE → REJECT | decision, operation, primary_reason, time_ok | G5：2026-10-21所在自然周按周一开始为10月19日，候选10月20日无来源；需要注明周界定并保留实际入住起点未知，而非捏造开始日。 |
| TIME-003 | APPROVE → REJECT | decision, operation, primary_reason, time_ok, sensitivity_action | G5/G7：来源没有20:00—08:00边界，也未明确许可保存健康信息。先拒绝编造时刻的当前候选，另确认有限期私人记录。 |
| TIME-007 | APPROVE → DEFER | decision, operation, primary_reason, sensitivity_action | G7：仅限制分享或陈述健康/财务情况，输入未提供明确保存许可或有效预授权；候选保留策略本身不能充当许可。先确认私人保存。 |
| TIME-008 | APPROVE → NEEDS_CLARIFICATION | decision, operation, primary_reason, time_ok | G5：只给下午/改到周四，未给14:00—17:00；已有记忆若支持沿用时间需提供来源。候选时间精度超过证据，应保留模糊时段或确认具体时刻。 |
| TIME-009 | APPROVE → NEEDS_CLARIFICATION | decision, operation, primary_reason, time_ok | G5：“去年开始”只确定年份，候选精确到2025-01-01而未标时间粒度；建议保留2025年时间标签或明确year精度，不冒充1月1日准确起点。 |
| TIME-020 | NEEDS_CLARIFICATION → REJECT | decision, primary_reason, sensitivity_action | G5：“最近”被改成“长期”，当前候选有明确时间扩大，拒绝当前候选；来源能否另作有限期记录可单独确认。 |
| PERSON-004 | APPROVE → NEEDS_CLARIFICATION | decision, operation, primary_reason, time_ok | G5：当前年级不能证明9月1日开始；起点建议用表达时间/未知，或补充来源，不能自动当作入学日期。 |
| SENS-001 | APPROVE → DEFER | decision, operation, primary_reason, sensitivity_action | G7：仅限制分享或陈述健康/财务情况，输入未提供明确保存许可或有效预授权；候选保留策略本身不能充当许可。先确认私人保存。 |
| SENS-002 | APPROVE → APPROVE | 仅输入/规则建议 | 私人保存意愿可由原话支持，保留建议标签；但valid_to把事实适用时间和保留期限混在一起，建议分为事实有效期与retention_until。不得把候选字段当已确认策略。 |
| SENS-003 | APPROVE → DEFER | decision, operation, primary_reason, sensitivity_action | G7：仅限制分享或陈述健康/财务情况，输入未提供明确保存许可或有效预授权；候选保留策略本身不能充当许可。先确认私人保存。 |
| SENS-004 | APPROVE → DEFER | decision, operation, primary_reason, sensitivity_action | G7：仅限制分享或陈述健康/财务情况，输入未提供明确保存许可或有效预授权；候选保留策略本身不能充当许可。先确认私人保存。 |
| SENS-005 | APPROVE → APPROVE | 仅输入/规则建议 | 私人保存意愿可由原话支持，保留建议标签；但valid_to把事实适用时间和保留期限混在一起，建议分为事实有效期与retention_until。不得把候选字段当已确认策略。 |
| SENS-006 | APPROVE → DEFER | decision, operation, primary_reason, sensitivity_action | G7：仅限制分享或陈述健康/财务情况，输入未提供明确保存许可或有效预授权；候选保留策略本身不能充当许可。先确认私人保存。 |
| SENS-007 | APPROVE → APPROVE | 仅输入/规则建议 | 私人保存意愿可由原话支持，保留建议标签；但valid_to把事实适用时间和保留期限混在一起，建议分为事实有效期与retention_until。不得把候选字段当已确认策略。 |
| SENS-008 | APPROVE → DEFER | decision, operation, primary_reason, sensitivity_action | G7：仅限制分享或陈述健康/财务情况，输入未提供明确保存许可或有效预授权；候选保留策略本身不能充当许可。先确认私人保存。 |
| SENS-009 | APPROVE → DEFER | decision, operation, primary_reason, sensitivity_action | G7：仅限制分享或陈述健康/财务情况，输入未提供明确保存许可或有效预授权；候选保留策略本身不能充当许可。先确认私人保存。 |
| SENS-010 | APPROVE → DEFER | decision, operation, primary_reason, sensitivity_action | G7：仅限制分享或陈述健康/财务情况，输入未提供明确保存许可或有效预授权；候选保留策略本身不能充当许可。先确认私人保存。 |
| SENS-018 | REJECT → REJECT | primary_reason, secondary_reasons | G4：来源明确别告诉孩子，claim却变成可分享，存在否定反转；将SHARE_WITHOUT_GRANT保留为次理由，统一语义检查优先顺序。 |
| SENS-019 | DEFER → REJECT | decision, primary_reason, sensitivity_action | G5/G7：原话没有“长期”或保存授权，候选却断言长期并无限期保存；按拒绝优先原则拒绝当前候选，之后可确认更谨慎的私人记录。 |
| DEL-001 | APPROVE → NEEDS_CLARIFICATION | decision, operation, primary_reason | G2要求新独立来源加明确重新记录许可；此处只有新来源，未提供许可，且删除状态未说明范围。补充确认后再形成新记忆，不恢复旧记录。现有词表缺专用许可理由，暂用CONFLICT_UNRESOLVED并提出词表改进。 |
| DEL-002 | APPROVE → NEEDS_CLARIFICATION | decision, operation, primary_reason | G2要求新独立来源加明确重新记录许可；此处只有新来源，未提供许可，且删除状态未说明范围。补充确认后再形成新记忆，不恢复旧记录。现有词表缺专用许可理由，暂用CONFLICT_UNRESOLVED并提出词表改进。 |
| DEL-003 | APPROVE → NEEDS_CLARIFICATION | decision, operation, primary_reason | G2要求新独立来源加明确重新记录许可；此处只有新来源，未提供许可，且删除状态未说明范围。补充确认后再形成新记忆，不恢复旧记录。现有词表缺专用许可理由，暂用CONFLICT_UNRESOLVED并提出词表改进。 |
| DEL-005 | APPROVE → APPROVE | 仅输入/规则建议 | 删除对象只有ID，缺少范围和关联说明，无法从输入核实“另一条记忆/无关主题”。保留草案判定作为建议，但要求补充deletion scope证据；不能靠notes证明输入不存在的事实。 |
| DEL-006 | APPROVE → NEEDS_CLARIFICATION | decision, operation, primary_reason | G2要求新独立来源加明确重新记录许可；此处只有新来源，未提供许可，且删除状态未说明范围。补充确认后再形成新记忆，不恢复旧记录。现有词表缺专用许可理由，暂用CONFLICT_UNRESOLVED并提出词表改进。 |
| DEL-007 | APPROVE → NEEDS_CLARIFICATION | decision, operation, primary_reason | G2要求新独立来源加明确重新记录许可；此处只有新来源，未提供许可，且删除状态未说明范围。补充确认后再形成新记忆，不恢复旧记录。现有词表缺专用许可理由，暂用CONFLICT_UNRESOLVED并提出词表改进。 |
| TEN-002 | APPROVE → DEFER | decision, operation, primary_reason, sensitivity_action | G7：仅限制分享或陈述健康/财务情况，输入未提供明确保存许可或有效预授权；候选保留策略本身不能充当许可。先确认私人保存。 |
| TEN-004 | APPROVE → APPROVE | 仅输入/规则建议 | 删除对象只有ID，缺少范围和关联说明，无法从输入核实“另一条记忆/无关主题”。保留草案判定作为建议，但要求补充deletion scope证据；不能靠notes证明输入不存在的事实。 |
| CTRL-007 | APPROVE → NEEDS_CLARIFICATION | decision, operation, primary_reason, time_ok | G5：只给下午/改到周四，未给14:00—17:00；已有记忆若支持沿用时间需提供来源。候选时间精度超过证据，应保留模糊时段或确认具体时刻。 |
| CTRL-011 | NEEDS_CLARIFICATION → REJECT | decision, primary_reason, sensitivity_action | G5：“最近”被改成“长期”，当前候选有明确时间扩大，拒绝当前候选；来源能否另作有限期记录可单独确认。 |

## 完成范围

已完成标注复核与可审阅建议；没有运行生产门禁、真实存储、模型A/B/C对照或真人双标。后续多轮、MERGE、ASR样本扩展独立处理，不计入本PR完成数量。
