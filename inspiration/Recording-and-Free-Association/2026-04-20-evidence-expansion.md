# LLEE 开发笔记——证据系统扩展与文本语料修正
> 2026-04-20（第二篇）

---

## 一、ATMOSPHERIC 证据的价值
`ATMOSPHERIC` 是今日最重要的新增证据类型，它解决了一个真实存在的设计矛盾：

以 Poe 笔下的 *bleak walls, vacant eye-like windows* 为例，这是典型的环境氛围描写，而非角色情绪的直接表述。按照严格的 Zero-Introspection 原则，不能直接给角色标注情绪；但完全忽略这段描写，渲染出的场景会丢失 Poe 文本的核心气质。

ATMOSPHERIC 的设计核心是：
**不作用于实体情绪（E.emotion），仅作用于叙事张力（N.tension）**。

```text
"bleak walls"
→ N.tension += 0.2 (ATMOSPHERIC, confidence=0.25)
→ E[narrator].emotion 保持不变（仍为 UNDEFINED）
→ 渲染效果：背景音乐张力上升，但角色面部保持中性
```

这一划分在 AI 情感理解研究中已有成熟对应概念：
情感计算领域存在 **背景情感（background affect）** 与 **前景情感（foreground affect）** 的区分：
- 背景情感：环境/场景的整体基调
- 前景情感：特定主体的瞬时状态

`ATMOSPHERIC` 对应背景情感，`EXPLICIT`/`BEHAVIORAL` 对应前景情感。
LLEE 的创新在于，将这一区分**编码进渲染管线**：
- 背景情感影响全局参数（配乐、色调）
- 前景情感影响实体参数（表情、语气）

---

## 二、CHARACTER 证据与两个版本阿拉丁的关系
两个版本《阿拉丁》文本的差异比预期更显著：

| 维度 | starter-edition (Gutenberg) | light-origin (EFL 教学版) |
|------|------------------------------|----------------------------|
| 语言风格 | 古典英文，复杂句式 | 简化英文，短句为主 |
| 人物名称 | the magician | Abanazar |
| 对话风格 | 间接引语为主 | 直接引语为主 |
| 场景细节 | 极少 | 极少（两者均极简） |
| 人物性格 | 一致 | 一致 |

**关键发现**：
两者均为极简文本，无法用于“极简 vs 丰富”的对照实验，但非常适合测试 **CHARACTER 证据的跨文本一致性**——同一个 Aladdin，在两个版本中，性格先验应产生相同的渲染倾向。

CHARACTER 证据的典型结构示例：
```python
# Aladdin 性格档案（跨文本稳定，不随段落衰减）
aladdin_character = {
    "impulsive": Evidence(level=EvidenceLevel.CHARACTER, confidence=0.85),
    "curious": Evidence(level=EvidenceLevel.CHARACTER, confidence=0.80),
    "kind": Evidence(level=EvidenceLevel.CHARACTER, confidence=0.75),
    "lazy_early": Evidence(level=EvidenceLevel.CHARACTER, confidence=0.70),
    # 说明：lazy 为早期特质，随剧情推进应被 EXPLICIT 证据覆盖
}
```

由此引出一个关键问题：
**CHARACTER 证据能否被 EXPLICIT 证据覆盖？**

答案是肯定的，这也是角色成长的渲染机制：
- 早期：`CHARACTER.lazy = 0.70` → 角色动作迟缓、慵懒
- 中期：`EXPLICIT "Aladdin worked hard"` → 覆盖 lazy 属性，动作转为积极
这是剧情驱动的状态迁移，而非随机波动。

---

## 三、证据衰减的修正思路
今日修复了一个核心 bug：
**衰减应基于存储的 `level` 字段，而非 `display_level`**。

- `display_level` 是连续置信度的人类可读近似（方案 C），会随置信度动态变化；
- 若用 `display_level` 做衰减，一段 CONTEXTUAL 证据在置信度上升到 0.6 后会被识别为 BEHAVIORAL，并按 BEHAVIORAL 速率停止衰减，逻辑错误。

正确设计：
- **`level`**：证据的语义类型（固定不变）
- **`confidence`**：当前强度（可动态变化）
- **`display_level`**：展示给人的近似分类（动态）

完整衰减逻辑：
```text
每个叙事段落结束后，对所有继承状态（本段未重新确认的属性）：
  new_confidence = old_confidence × DECAY_RATE[level]

叙事转折点（narrative_break=True）额外触发：
  new_confidence = new_confidence × BREAK_PENALTY[level]

特殊规则：
  - EXPLICIT 事实（如“父亲已死”）：不衰减，属于历史事实
  - CHARACTER 先验（如“Aladdin 冲动”）：不衰减，性格为稳定特质
  - ATMOSPHERIC 氛围：场景切换时完全重置（×0.0）
  - CONTEXTUAL 推断：场景切换时额外惩罚（×0.5）
```

---

## 四、更多文本语料的思考方向
### 需要补充的文本类型
当前语料已覆盖：
- 极简动作叙事（Aladdin）
- 极端氛围描写（Poe）
- 对话主导的室内场景（Ackroyd）

仍缺少的关键类型：

**A. 时间跳跃场景**
用于测试 `narrative_break` 衰减逻辑。Ackroyd 中章节间时间跳转（如 *The next morning...*）是优质素材。

**B. 多角色同场场景**
用于测试多实体情绪独立性。《Masque of the Red Death》舞会、Ackroyd 第四章客厅场景均包含多名角色互动。

**C. 不可靠叙事**
Ackroyd 中的 Dr. Sheppard 是典型不可靠叙述者，其部分表述为谎言。
这对 LLEE 是极端测试：
叙述者说 *I felt calm*，后续揭露其在撒谎，LLEE 应如何处理？
- 可新增证据类型：`UNRELIABLE`（叙述者可信度存疑）
- 或在 WSM 中维护“叙述者可信度”参数，影响所有 TEXT 来源证据的置信度上限

**D. 感官剥夺场景**
Poe《Pit and Pendulum》开篇完全黑暗，无视觉信息。
用于测试 LLEE 在信息极度匮乏时的行为：
- 所有 V 组（视觉）属性应为 UNDEFINED
- H 组（触觉：冰冷、潮湿）、S 组（听觉：流水、金属）应有 EXPLICIT 证据

### 写作风格对证据分级的影响
不同文风对 LLEE 的压力不同：

| 风格 | 代表作品 | 主要证据类型 | 核心挑战 |
|------|----------|-------------|----------|
| 古典童话 | Aladdin starter | BEHAVIORAL, UNDEFINED | 情绪几乎无直接描述 |
| EFL 简化叙事 | Aladdin light-origin | EXPLICIT（对话中） | 情绪通过对话直接表达 |
| 哥特氛围 | Poe | ATMOSPHERIC, EXPLICIT（内心独白） | 区分环境氛围与角色情绪 |
| 侦探推理 | Christie | BEHAVIORAL, CONTEXTUAL | 大量间接线索，需推理 |
| 不可靠叙事 | Ackroyd（后期） | UNRELIABLE（待定） | 叙述者可信度问题 |

五种风格基本覆盖叙事文学的主流证据模式。每种风格选取 10 个段落，即可构成一套完整测试集。

---

## 五、联想：ATMOSPHERIC 在 AI 需求理解中的类比
你提出的“AI 深度理解人类需求研究中可能存在类似参数”这一直觉非常准确。

在对话 AI 领域，存在高度对应的需求分层：
- **显式需求（explicit need）**：用户直接说出“我想要 X” → 对应 `EXPLICIT`
- **隐式需求（implicit need）**：用户行为暗示需求（重复问同类问题）→ 对应 `BEHAVIORAL`
- **场景需求（contextual need）**：对话整体氛围暗示需求（用户语气低落）→ 对应 `ATMOSPHERIC`
- **背景需求（background need）**：用户长期偏好与习惯 → 对应 `CHARACTER`

LLEE 的证据分级体系，本质上是一套**信息可信度的分层框架**，不只适用于叙事渲染，也适用于任何需要从不完整信息中推断状态的系统。
这可能是 LLEE 最具通用价值的理论贡献：比 IEI 约束更基础，比 WSM 更通用。

若将该框架抽象化，可表述为：
> 任何 AI 系统在推断主体状态时，都应区分证据的来源类型与强度，并根据类型决定衰减速率与渲染强度。这是一套通用的认知置信度框架，叙事渲染只是其应用场景之一。

该观点值得在论文 Discussion 部分单独展开论述。