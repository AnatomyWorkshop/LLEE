# LLEE 开发记录 — 语料验证与策略

> 2026-04-21

---

## 一、语料全景

| 文本 | 词数 | 作者 | 感官密度 | 对话密度 | 环境描写 | 情绪表达 | 特殊价值 |
|------|------|------|---------|---------|---------|---------|---------|
| Sakakibara Kaito (full) | 8,665 | AI | HIGH | MEDIUM | RICH | MIXED | AI 生成基准 |
| Sakakibara Kaito (starter) | 1,520 | AI | MEDIUM | MEDIUM | MODERATE | MIXED | 同故事精简版 |
| Aladdin (light-origin) | 5,356 | 人类 | MEDIUM | HIGH | MODERATE | EXPLICIT | 对话主导 |
| Aladdin (starter) | 5,279 | 人类 | LOW | HIGH | SPARSE | EXPLICIT | 极稀疏叙事 |
| Cask of Amontillado | 2,483 | Poe | EXTREME | MEDIUM | RICH | BEHAVIORAL | 不可靠叙述者 |
| The Missing Will | 3,417 | Christie | MEDIUM | HIGH | MODERATE | EXPLICIT | 短篇侦探 |
| Secret of Chimneys | 74,778 | Christie | MEDIUM | HIGH | MODERATE | MIXED | 长篇冒险 |
| Poe Vol.2 | 95,210 | Poe | EXTREME | MEDIUM | RICH | ATMOSPHERIC | 极端大气描写 |
| Call of Cthulhu | 12,134 | Lovecraft | EXTREME | LOW | RICH | ATMOSPHERIC | 宇宙恐怖 |
| Roger Ackroyd | 70,909 | Christie | MEDIUM | HIGH | MODERATE | EXPLICIT | 不可靠叙述者 |

总计约 280,000 词，覆盖 4 位人类作者 + 1 个 AI 生成源。

---

## 二、AI 生成小说的评估

Sakakibara Kaito 的两篇文本读下来，AI 痕迹明显但文本质量不低：

优点：
- 感官描写丰富且功能性强（雨、光、温度都服务于情绪）
- full 版和 starter 版是同一故事的两种详细程度——**这正是双语料实验需要的对齐关系**
- 环境描写有具体细节（"cherry blossom petals stick to the pavement like wet confetti"）

AI 特征：
- 隐喻重复（"space between" 模式多次出现）
- 情绪过度解释（先展示再解释，人类作者通常只做一个）
- 对话缺乏角色区分度（Kaito 和 Watanabe 的说话方式太相似）
- 结构节奏均匀（Part One/Two/Three 的长度和节奏几乎一致）

**关键判断：AI 小说可以作为语料，但需要明确标注为 AI 生成，并且在论文中作为一个独立的实验维度。**

理由：LLEE 的 Parser 本身就是 LLM。用 AI 生成的文本测试 LLM Parser，可以回答一个有趣的问题——**LLM 解析 AI 生成的文本时，是否比解析人类文本更准确？** 如果是，说明 LLM 对自己的"语言习惯"有偏好；如果不是，说明 LLEE 的 Schema 约束足够强，能抹平这种差异。

---

## 三、语料验证：Gate 0 能通过吗？

Gate 0 要求：信息单元比 > 1.5 OR 词数比 > 2.0

### 对齐对 1：Sakakibara full (8,665w) vs starter (1,520w)

词数比 = 5.7，远超 2.0。同一故事的两种详细程度，事件序列完全对齐。

**这是目前最干净的双语料对。** 比 Aladdin 的两个版本更好——Aladdin 的两个版本词数几乎相同（5,356 vs 5,279），不是"精简 vs 丰富"的关系，而是两种不同的改写。

### 对齐对 2：Aladdin light-origin (5,356w) vs starter (5,279w)

词数比 = 1.01。**不满足 Gate 0。** 两者是同一故事的不同改写，不是不同详细程度。

但它们仍然有价值：测试 CHARACTER 证据的跨语料一致性（同一角色在两个版本中的性格先验应该一致）。

### 跨故事对比：Poe (EXTREME) vs Aladdin starter (LOW)

不是同一故事，无法做事件级对齐。但可以做**风格级对比**：同样是"角色进入一个封闭空间"，Poe 的描写和 Aladdin 的描写在信息密度上差异极大。

---

## 四、策略建议：单一故事深度 vs 多故事广度

你问的核心问题是：**着重添加单一故事语料的范围，还是不同故事？**

**建议：两者都需要，但优先级不同。**

### 优先级 1：单一故事的精简/丰富对（Gate 0 必需）

Sakakibara Kaito 的 full/starter 对已经满足 Gate 0。但只有一对不够——需要至少 3 对来做统计检验。

可以从现有语料中构造更多对：
- 从 Poe 的 Cask of Amontillado（2,483w）中选 5 个段落，手写精简版（每段压缩到 1/3）
- 从 Lovecraft 的 Cthulhu（12,134w）中选 5 个段落，手写精简版
- Sakakibara 的 full/starter 已经有了

这样就有 3 个故事 × 5 段 = 15 对精简/丰富对齐段落。

### 优先级 2：多故事广度（Phase 1 保真度实验需要）

Phase 1 需要测试 LLEE 在不同写作风格下的表现。当前语料已经覆盖了：

```
维多利亚童话叙事：Aladdin（稀疏动作）
哥特大气描写：Poe（极端感官）
宇宙恐怖：Lovecraft（累积性恐惧，低对话）
侦探推理：Christie（对话主导，行为证据）
AI 生成轻小说：Sakakibara（现代日常，混合情绪）
```

**5 种风格已经足够。** 不需要再加新故事。需要的是从每种风格中选出 8-10 个代表性段落，总共 40-50 段。

### 优先级 3：未来扩充方向

如果后续要扩充，优先考虑：
- **感官剥夺场景**：Poe 的 Pit and Pendulum（已在 Vol.2 中）——完全黑暗，无视觉信息
- **多角色同场景**：Christie 的晚宴场景——测试多实体情绪独立性
- **时间跳跃**：Ackroyd 的章节间跳跃——测试 narrative_break 衰减

这些都可以从现有长篇中截取，不需要新语料。

---

## 五、AI 生成语料的特殊实验价值

Sakakibara 的文本引出了一个计划中没有的实验维度：

**实验 X：Parser 对 AI 生成文本 vs 人类文本的表现差异**

```
假设 Hx：LLM Parser 解析 AI 生成文本时，证据分级一致性更高
  （因为 AI 文本的情绪表达更"标准"，更容易被 LLM 识别）

测量：
  - 5 段 AI 文本 × 20 次 → 证据一致性 A
  - 5 段人类文本 × 20 次 → 证据一致性 B
  - 比较 A vs B

如果 A > B：
  → LLM 对自己的"语言习惯"有偏好
  → 这是 LLEE 需要警惕的偏差——AI 生成的叙事可能被过度"理解"

如果 A ≈ B：
  → LLEE 的 Schema 约束足够强，抹平了文本来源的差异
  → 这是 LLEE 作为"通用中间表示"的证据
```

这个实验几乎不增加工作量（只需要在 Phase 0.5 的稳定性测试中多跑 5 段 AI 文本），但论文价值很高——它直接回应了"AI 生成内容的可信度"这个热门话题。

---

## 六、地基状态评估

### 已完成
- Schema（6 类证据 + 7 组世界状态 + Delta 格式）✓
- WSM（衰减 + 置信度上限 clamp + narrative_break）✓
- Parser prompt 模板（证据规则 + 环境提取 + Zero-Introspection）✓
- 稳定性测试脚手架 ✓
- 7/7 测试通过 ✓
- 语料选取（5 种风格，10 个文本）✓

### Gate 0 状态
- Sakakibara full/starter 对满足词数比 > 2.0 ✓
- 但只有 1 对，需要至少 3 对 → 需要从 Poe/Lovecraft 手写精简版
- 信息单元标注未开始 → 需要人工标注

### 可以开始的工作
- **Phase 0.5 稳定性测试**：不依赖语料对齐，只需要 5 个任意段落。可以现在跑。
- **从现有语料中选段落**：从 5 种风格中各选 8-10 段，建立段落库。
- **Sakakibara 的 AI 文本实验**：在稳定性测试中加入 AI 文本段落。

### 还不能开始的工作
- Phase 1 保真度实验：需要 ground truth 标注（人工）
- Phase 2 渲染：需要 Three.js 适配器（代码）

**结论：地基可以打了。** 下一步是跑 Phase 0.5 稳定性测试 + 从语料中选段落建库。语料对齐的精简版手写可以和稳定性测试并行。

---

## 八、Phase 0.5 执行状态

### 段落库扩展完成

corpus_selections.py 从 5 段扩展到 12 段，覆盖 6 种风格：

```
fairy_tale:           2 段（Aladdin）
gothic:               3 段（Poe: Usher, Masque, Cask）
cosmic_horror:        1 段（Lovecraft: Cthulhu 开篇）
detective:            1 段（Christie: Ackroyd 早餐）
light_novel:          2 段（Sakakibara: full/starter 教室场景）
second_person_sensory: 3 段（Karl: 教室感官、走廊社交、内心恐慌）
```

Human 7 段 + AI 5 段。AI 段落专门用于测试 Parser 对 AI 文本 vs 人类文本的表现差异。

### Karl 的特殊价值

Karl.txt（1,638 词，66 行）是第二人称叙事，感官密度极高。它对 LLEE 的挑战：

1. **第二人称**：当前 schema 的 Entity 假设第三人称。"You feel" 的主语是谁？
   → 需要在 Parser prompt 中明确：第二人称的 "you" 映射为主角实体

2. **超自然元素**：Karl 有"预知未来"的能力（Vision A/B/C）。这些幻象是世界事实吗？
   → 不是。它们是角色的主观体验，应标注为 CONTEXTUAL（置信度低）
   → 只有"真实发生的"场景才是 EXPLICIT

3. **极端感官密度**：一段话里同时有触觉（linoleum floor）、听觉（scraping sound）、
   视觉（golden light）、嗅觉（chalk dust）。这是环境填充率测试的理想素材。

### Dry-run 结果

```
12/12 segments PASS（dry-run 模式，无 API 调用）
7/7 单元测试 PASS
```

### 下一步

设置 ANTHROPIC_API_KEY 后运行：
```bash
python -m llee.stability_test --runs 5    # 快速验证（60 次调用）
python -m llee.stability_test --runs 20   # 完整验证（240 次调用）
```

### Lovecraft 对 LLEE 的特殊挑战

Cthulhu 的写作风格和 Poe 不同。Poe 是"我看到了恐怖的东西"（EXPLICIT + BEHAVIORAL），Lovecraft 是"有些东西不应该被看到"（ATMOSPHERIC + 否定式描写）。

```
Poe: "a sense of insufferable gloom pervaded my spirit"
  → EXPLICIT（叙述者直接陈述内心状态）

Lovecraft: "the most merciful thing in the world is the inability of the human mind
            to correlate all its contents"
  → 这是什么证据类型？
  → 不是 EXPLICIT（没有陈述情绪）
  → 不是 BEHAVIORAL（没有行为）
  → 不是 ATMOSPHERIC（不是环境描写）
  → 是 CONTEXTUAL？（从"人类心智的局限"推断出恐惧？）
  → 还是一种新的类型：PHILOSOPHICAL（哲学性陈述暗示世界观）？
```

Lovecraft 的文本可能暴露 LLEE 证据分级系统的一个盲区：**抽象陈述**。当叙述者不描述具体场景、不表达具体情绪、而是发表哲学性评论时，LLEE 应该如何处理？

当前最合理的处理：标注为 CONTEXTUAL（弱推断），置信度 0.3-0.4。哲学性陈述暗示了叙述者的世界观，但不直接描述可渲染的世界状态。渲染器可以通过整体色调（冷色、低饱和度）来反映这种世界观，但不应该给任何实体分配具体情绪。

这值得在 Phase 1 的保真度实验中专门测试。

### AI 文本的"过度解释"与 LLEE 的关系

Sakakibara 的文本有一个有趣的特征：情绪先展示再解释。

```
人类作者（Poe）：
  "I know not how it was—but, with the first glimpse of the building,
   a sense of insufferable gloom pervaded my spirit."
  → 一次性陈述，EXPLICIT

AI 作者（Sakakibara）：
  "Her expression was unreadable—the kind of face that held its secrets close,
   like a fist curled around something precious and breakable."
  → 先说"unreadable"（BEHAVIORAL），再用比喻解释（ATMOSPHERIC？）
  → 同一句话包含两种证据类型
```

这对 Parser 是一个挑战：同一句话中的多重证据应该如何处理？当前 prompt 没有明确规则。

建议：在 prompt 中增加一条规则——**当同一句话包含多种证据类型时，取最高置信度的类型作为主证据，其他作为辅助证据（confidence × 0.5）。**
