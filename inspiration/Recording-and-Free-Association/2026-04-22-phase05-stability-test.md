# LLEE 开发笔记 — Phase 0.5 稳定性测试实战

> 2026-04-22

---

## 一、多模型 Smoke Test

### 连通性测试

4 个 API 全部连通，通过 OpenAI 兼容接口统一调用：

| Provider | Base URL | 模型 | 连通 |
|----------|----------|------|------|
| ZhipuAI | open.bigmodel.cn/api/paas/v4 | glm-4.5-air | ✓ |
| DeepSeek | api.deepseek.com/v1 | deepseek-chat / deepseek-reasoner | ✓ |
| Anthropic relay | lanyiapi.com/v1 | claude-opus-4-6 / claude-sonnet-4-6 | ✓ |
| Volcengine | ark.cn-beijing.volces.com/api/v3 | doubao-seed-2-0-pro | ✓ |

### 单轮 Schema 合规率（normalizer 修复后）

| 模型 | Pass/12 | 主要失败原因 |
|------|---------|------------|
| GLM-4.5-air | 10/12 | 偶发 position/stage 格式 |
| DeepSeek Chat | 10/12 | narrative.stage 枚举 |
| Claude Opus 4.6 | 10/12 | reverb 枚举 |
| DeepSeek Reasoner | 5/12 | 推理模型不输出最终 JSON |
| Claude Sonnet 4.6 | 2/12 | reverb 枚举 + 连接不稳定 |

**关键发现**：三个非推理模型（GLM、DeepSeek Chat、Claude Opus）表现相当，失败段落互不重叠。DeepSeek Reasoner 不适合结构化输出任务。

---

## 二、Normalizer 演进

LLM 输出的 JSON 结构正确但字段类型经常不匹配 Pydantic 严格验证。构建了一个 `normalize_delta()` 预处理器，覆盖了以下边界：

```
position: dict{x,y,z}/list → tuple
state: dict → string
action: string → dict{verb}
sonic.reverb: 非枚举值 → 最近枚举映射（large_hall→room_large 等）
sonic.ambient_sounds: string → dict, 补 id/sound_type
visual.atmosphere: string/list → dict
visual.scene_type_evidence: string/空字符串 → Evidence dict
visual.lights: string → dict, 补 id, direction 容错
narrative.stage: 非枚举值 → 最近映射（rising_action→rising 等）
evidence.source: 非枚举值 → 最近映射（narrative→text 等）
evidence.level: 非枚举值 → 最近映射（implied→contextual 等）
```

这个 normalizer 本身就是论文素材——它记录了"LLM 在结构化输出中最常犯的类型错误"。

---

## 三、GLM-4.5-air 5 轮一致性测试（3 轮迭代）

### 第 1 轮（基础 normalizer）
2/12 PASS。主要问题：compliance 低（evidence.source 枚举不匹配）+ emotion 一致性低。

### 第 2 轮（+source/level 映射）
2/12 PASS。Compliance 大幅提升，暴露了真正的一致性问题。

### 第 3 轮（+prompt 修复：情绪词表、意图≠情绪、抽象文本规则、枚举约束）
**4/12 PASS**。

| Segment | Compliance | Evidence | Emotion | Status |
|---------|-----------|----------|---------|--------|
| aladdin_cave_sparse | 100% | 84% | 100% | **PASS** |
| aladdin_lamp_sparse | 100% | 87% | 70% | FAIL |
| usher_approach_rich | 80% | 100% | 50% | FAIL |
| masque_rooms_rich | 100% | 100% | 100% | **PASS** |
| cask_unreliable | 100% | 85% | 83% | FAIL |
| cthulhu_philosophical | 100% | 100% | 100% | **PASS** |
| ackroyd_neutral | 80% | 94% | 100% | FAIL |
| sakakibara_rich | 100% | 100% | 100% | **PASS** |
| sakakibara_sparse | 100% | 100% | 60% | FAIL |
| karl_sensory | 80% | 94% | 100% | FAIL |
| karl_hallway | 100% | 90% | 60% | FAIL |
| karl_panic | 100% | 88% | 85% | FAIL |

### Prompt 修复效果

cask_unreliable 的 emotion 从 60%→83%（"意图≠情绪"规则生效）
cthulhu 从 evidence 62%→100%（"抽象文本→UNDEFINED"规则生效）
karl_panic 从 emotion 73%→85%（情绪词表约束减少了同义词波动）

---

## 四、GLM 的自我分析

GLM-4.5-air 对自己的测试结果做了一份分析（D:\LLEE\inspiration\response\2024-4-22-GLM-chat.md），核心观点：

1. **Compliance 失败是偶发注意力漂移**，不是系统性问题——同一段落的 run 0 失败但 run 1-4 通过
2. **cask 的情绪漂移**是"推理和事实的边界"问题——Montresor 在冷静地计划谋杀，模型在 UNDEFINED 和 malicious 之间摇摆
3. **cthulhu 的证据漂移**是"文本本身的可判性极限"——纯哲学段落不适合做稳定性测试输入
4. **建议把 cthulhu 和 ackroyd 移到 Phase 1 作为"困难样本"**

第 4 点值得采纳。Phase 0.5 的目的是验证 prompt 的结构稳定性，不是验证对极端文本的判断能力。

---

## 五、Phase 0.5 判定

**严格标准（12/12 PASS）：未通过。**
**实际状态：4/12 PASS，8/12 的 compliance 平均 95%，evidence 平均 93%，emotion 平均 80%。**

剩余问题分三类：
1. **Compliance 偶发失败**（position 格式）：normalizer 可继续加固，但边际收益递减
2. **Emotion 一致性 60-70%**（usher、sakakibara_sparse、karl_hallway）：模型固有噪声，prompt 迭代空间有限
3. **Emotion 一致性 80-85%**（cask、karl_panic）：接近阈值，再迭代 1-2 轮可能通过

**建议：以当前状态进入 Phase 1，同时记录所有 prompt 版本和稳定性数据作为论文素材。** Phase 0.5 的价值不在于"通过/不通过"，在于暴露了哪些文本类型对 Parser 最具挑战性——这本身就是一个研究发现。

---

## 六、对 GLM 分析的回应

GLM 的分析质量很高，但有一个盲点：它建议把困难样本移出 Phase 0.5，这在工程上合理，但在学术上不够诚实。论文应该报告所有段落的结果，包括失败的，然后分析失败原因。"哲学文本的证据分级不稳定"本身就是一个有价值的发现——它指向了 LLEE 证据系统的适用边界。

---

## 七、Prompt 迭代记录

### v1（初始版本）
- 6 类证据定义 + Zero-Introspection + 输出格式
- 5 条 Critical Rules

### v2（本轮修复）
新增 6 条规则：
- Rule 6: 环境提取强制扫描
- Rule 7: 战略意图 ≠ 情绪状态
- Rule 8: 抽象/哲学文本 → UNDEFINED + ATMOSPHERIC
- Rule 9: 标准情绪词表（15 个标签）
- Rule 10: reverb 枚举约束
- Rule 11: narrative.stage 枚举约束

### 效果
- cask emotion: 60% → 83%
- cthulhu evidence: 62% → 100%
- karl_panic emotion: 73% → 85%
- 整体 compliance: ~75% → ~95%
