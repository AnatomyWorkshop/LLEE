# LLEE 开发笔记——Phase 0.5 Parser Prompt 模板
> 2026-04-20（第三篇）

---

## 一、本次完成的工作
### 新增文件
**`src/llee/parser_prompt.py`** — Parser Prompt 模板系统
三大核心组件：
1. **`EVIDENCE_RULES`** — 6类证据的判定规则（内置于system prompt）
   - 每类证据的定义、示例、置信度上限
   - Zero-Introspection 原则的具体执行规则
   - ATMOSPHERIC 与 EXPLICIT 边界的明确说明

2. **`SYSTEM_PROMPT`** — Claude API 的系统提示
   - 角色定义：LLEE Parser，结构化世界状态提取器
   - 输出格式：WorldStateDelta JSON 结构规范
   - 置信度指南：每类证据的典型置信度区间
   - 5条关键规则（包含 ATMOSPHERIC 不修改 entity.emotion 的强制约束）

3. **`build_parse_prompt(passage, wsm, ...)`** — 完整提示构建器
   - 接收 WSM 实例，自动注入当前世界状态上下文
   - 支持 `narrative_break=True` 标记（在约束块中声明场景切换）
   - 返回 `(system, user)` 元组，直接传入 Claude API

**`src/llee/stability_test.py`** — Phase 0.5 稳定性验证脚本
```bash
#  Dry Run（测试脚本框架，不调用API）
python -m llee.stability_test --dry-run

# 正式验证：5个段落 × 20次 = 100次API调用
python -m llee.stability_test --runs 20
```

输出三大核心指标：
- Schema 合规率（目标 100%）
- 证据分类一致性（目标 >80%）
- 情绪标注一致性（目标 >90%）

### 新增测试
`test_parser_prompt_builder` — 验证提示包含必要关键词（ATMOSPHERIC、Zero-Introspection、WORLD STATE CONSTRAINT）
`test_narrative_break_decay` — 验证叙事转折点行为：
- CHARACTER 证据（confidence=0.85）在 narrative_break 后不衰减
- narrative.tension（ATMOSPHERIC 类型）在 narrative_break 后归零
**6/6 测试全部通过**

---

## 二、Prompt 设计的关键决策
### 为什么不使用 JSON Schema 强制约束？
Claude API 支持 `response_format: {type: "json_schema", json_schema: {...}}` 强制输出合规 JSON。
但 LLEE 的 WorldStateDelta 包含大量可选字段，强制 Schema 会导致模型输出大量 null 字段，增加 token 消耗且降低可读性。

当前方案：
在 system prompt 中提供 JSON 模板 + 明确说明**省略无证据字段**，随后在 Python 端用 Pydantic 验证。
既保持输出简洁，又有严格的后端校验。
若稳定性测试显示合规率 < 100%，再考虑切换到强制 JSON Schema 模式。

### ATMOSPHERIC 的 Prompt 表达
最核心的规则：**ATMOSPHERIC 证据只修改 N.tension，不修改 E.emotion**。
在 Prompt 中用加粗+独立段落强调：
```
**ATMOSPHERIC** (ceiling 0.30) — acts on N.tension ONLY, never on E.emotion
```

并在「Critical Rules」部分重复强调：
```
1. ATMOSPHERIC evidence NEVER updates entity.emotion — only narrative.tension
```

重复是必要的——大模型在长 Prompt 中容易遗忘早期规则。

### source_span 的设计
要求模型输出 `source_span: [start, end]`（字符偏移量），有两大价值：
1. **可解释性**：可以高亮显示哪段文本支撑了哪条证据
2. **验证性**：可以检查模型是否真的在引用文本，而非凭空推断

稳定性测试中不强制要求 source_span 精确（字符偏移量对大模型很难精准），但要求字段必须存在。

---

## 三、下一步计划
Phase 0.5 脚本框架已就绪，下一步执行：
1. **配置 ANTHROPIC_API_KEY** 并运行 `--runs 5` 快速验证
2. **根据结果迭代 Prompt**（若证据一致性 <80%，核心问题通常是 CONTEXTUAL/UNDEFINED 边界模糊）
3. **运行完整 20 次验证**，记录所有迭代版本（论文素材）

**Phase 1 准入条件**：
稳定性测试全部达标后，再启动文本标注和 Parser 准确率实验。

---

### 总结
1. 完成了**Prompt模板化+稳定性测试**的全套工程化方案，支持自动化验证
2. 确定了**轻量级JSON输出**的最优方案，兼顾性能与准确性
3. 核心规则（ATMOSPHERIC、衰减逻辑）已固化到Prompt和测试用例中
4. 流程清晰：先验证稳定性，再进入标注与实验阶段