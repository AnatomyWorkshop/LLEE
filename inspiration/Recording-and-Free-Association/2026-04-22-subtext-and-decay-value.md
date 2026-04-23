# LLEE 开发笔记 — 潜台词、衰减价值与忠实性边界

> 2026-04-22

---

## 一、对话潜台词：LLEE 不猜，但它记得

DeepSeek 的质疑：
> "我没事。"她说。LLEE 会输出 UNDEFINED，渲染一张中性脸。

这个质疑假设 LLEE 只看当前句。但 WSM 有记忆。

### 场景 A：孤立句

```
"我没事。"她说。
```

LLEE 输出：
- emotion = "fine", evidence = EXPLICIT (她直接说了), confidence = 0.85
- 渲染：中性表情，平稳语音
- 这是正确的。文本没有给任何行为线索暗示她在撒谎。

### 场景 B：有前文的句

```
[前一段] 她一直在哭，眼睛红肿。
[当前段] "我没事。"她说。
```

WSM 状态：
- 前一段：emotion = "sadness", evidence = BEHAVIORAL (哭泣), confidence = 0.8
- 衰减一轮后：confidence = 0.8 × 0.9 = 0.72（CONTEXTUAL 衰减率）
  等等——不对。"哭泣"是 BEHAVIORAL，BEHAVIORAL 不衰减（rate = 1.0）。
  所以 sadness 的 confidence 仍然是 0.8。

当前段：
- "我没事" → EXPLICIT, emotion = "fine", confidence = 0.85
- 但 WSM 里还有上一段的 sadness = 0.8

**这里有一个设计问题：当前段的 EXPLICIT "fine" 是否覆盖前一段的 BEHAVIORAL "sadness"？**

按当前 WSM 逻辑：`apply_delta` 中 `if eu.emotion is not None: entity.emotion = eu.emotion`——是的，直接覆盖。前一段的 sadness 被当前段的 fine 替换了。

**这是一个 bug 还是一个 feature？**

从 Zero-Introspection 的角度：当前文本说"我没事"，LLEE 应该尊重文本。覆盖是正确的。

但从叙事理解的角度：读者知道她在撒谎。前文的"哭泣"证据不应该被一句自我声明完全抹除。

### 解法：证据叠加而非覆盖

当前 WSM 对 emotion 是"最新值覆盖"。但如果改为"证据叠加"：

```python
# 当前设计：覆盖
entity.emotion = new_emotion  # 旧的 sadness 消失

# 改进设计：叠加（保留历史证据，取最高置信度或加权）
entity.emotion_stack = [
    Evidence(value="sadness", level=BEHAVIORAL, confidence=0.8),  # 前文
    Evidence(value="fine", level=EXPLICIT, confidence=0.85),       # 当前
]
# 渲染时：取最高置信度 → "fine" (0.85)
# 但 sadness (0.8) 仍然存在 → 渲染器可以做微妙处理
```

这不需要现在实现。但它指向了一个重要的架构方向：**emotion 不应该是单值，应该是证据栈。** 渲染器看到栈里有矛盾的证据（fine + sadness），可以选择：
- 保守渲染：取最高置信度（fine），中性脸
- 微妙渲染：两个证据都用，fine 驱动嘴型（微笑），sadness 驱动眼睛（微红）
- 这就是"潜台词"的渲染——不是猜测，是证据栈的矛盾

**这是六类型系统比二元系统更有价值的地方。** 二元系统只有"有证据/无证据"，无法表达"有两个矛盾的证据"。

---

## 二、六类型的增量价值：不在单段，在序列

DeepSeek 质疑：D（粗粒度）填充率 57% > F（完整）52%，六类型是否过度设计？

单段实验确实看不出六类型的价值。六类型的价值在**跨段落的状态继承和衰减**：

```
段落 1：Aladdin 进入洞穴。ATMOSPHERIC tension = 0.3
段落 2：他看到了灯。（没有提到氛围）
  → 二元系统：tension 要么保持要么消失，没有中间状态
  → 六类型系统：ATMOSPHERIC 衰减 0.3 × 0.7 = 0.21，氛围自然消散

段落 3：精灵出现。EXPLICIT tension = 0.9
段落 4：场景切换到地面。narrative_break = True
  → 二元系统：tension 要么保持要么消失
  → 六类型系统：ATMOSPHERIC → 0.0（完全重置），EXPLICIT → 0.9（不衰减）
  → 精灵出现的事实保留，但洞穴的氛围消失
```

**Phase 1 Round 2 需要用连续段落序列来展示这个差异。** 单段实验只能比较填充率，连续序列才能比较状态继承的质量。

---

## 三、敏感性分析：可以立即做

DeepSeek 要求：将衰减率上下浮动 20%，观察行为变化。

这不需要改代码——只需要在测试中临时修改 EVIDENCE_DECAY_RATE 的值：

```
基线：    ATMOSPHERIC=0.7, CONTEXTUAL=0.9
变体 +20%：ATMOSPHERIC=0.84, CONTEXTUAL=1.0（不衰减了！）
变体 -20%：ATMOSPHERIC=0.56, CONTEXTUAL=0.72
```

观察：在 50 段连续序列中，ATMOSPHERIC 状态的平均持续回合数。
- 如果 ±20% 导致持续回合数变化 > 50%，系统对参数高度敏感 → 需要校准
- 如果变化 < 20%，系统对参数不敏感 → 手设参数是可接受的近似

这可以在 Phase 1 Round 2 中做，不需要额外的 API 调用——只需要对已有的 Delta 序列重新跑 WSM。

---

## 四、"忠实"的定义：保守忠实 vs 完整忠实

DeepSeek 的第 6 点触及了根本：信任边界是"确保不犯错"还是"确保信息完整"？

LLEE 的答案是前者。这需要在论文中明确声明：

> LLEE 的忠实性是保守的、证据驱动的：它宁可遗漏文本中存在的信息（false negative），也不注入文本中不存在的信息（false positive）。这种不对称是有意为之的——在叙事渲染中，错误注入（IEI）比信息遗漏更难被用户察觉和纠正，因此 false positive 的代价高于 false negative。

这和医学诊断中的"宁可漏诊不可误诊"（高特异性优先于高灵敏度）是同一个设计哲学。

---

## 五、联想：证据栈与情绪的量子叠加

潜台词的本质是：一个角色同时处于多个情绪状态，直到渲染器"观测"时才坍缩为一个。

```
"我没事。"她说。
→ 证据栈：[fine(EXPLICIT, 0.85), sadness(BEHAVIORAL, 0.8)]
→ 渲染前：两个状态叠加
→ 渲染时：渲染器根据自己的"观测方式"选择坍缩方向
  - 面部渲染器：取 fine → 微笑
  - 声音渲染器：取 sadness → 声音微颤
  - 结果：嘴上微笑，声音发颤 = 潜台词
```

这和量子力学的叠加态有结构上的相似——不是比喻，是同一个数学结构（概率分布的叠加，观测导致坍缩）。

但这是 v2 的事。当前 v0.6 的 emotion 是单值覆盖，这是一个已知的简化。论文 Limitations 里应该加一句。
