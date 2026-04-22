# LLEE 与 Token 概率的数学同构——以及更深处的东西

> 2026-04-21
> 这篇文档不是技术规格，是一次思维实验。
> 它试图回答：LLEE 的置信度系统和 LLM 的 token 概率之间，是否存在比"看起来像"更深的联系？

---

## 一、表面的相似

把两个系统的核心公式放在一起：

```
LLM token 概率:
  P(token_i | context) = softmax(logit_i / T)
  logit_i = W·h + b    (线性变换 + 偏置)

LLEE 置信度:
  confidence = base × source_weight × decay^n
  render_intensity = f(confidence)    (分段线性映射)
```

形式上的对应关系：

| LLM | LLEE | 共同结构 |
|-----|------|---------|
| logit | base_confidence | 原始信号强度 |
| temperature T | source_weight | 信号的可信度缩放 |
| positional decay (attention) | decay^n | 距离衰减 |
| softmax → argmax | confidence → display_level | 连续 → 离散的投影 |
| vocabulary | EvidenceLevel 枚举 | 有限符号集 |
| context window | WSM history buffer | 有限记忆 |

这些对应不是巧合。它们指向一个共同的底层问题：**如何在有限信息下做出有置信度的判断**。

---

## 二、更深的同构：信息衰减的物理学

LLM 的 attention 机制有一个经验事实：远处的 token 对当前预测的贡献衰减。不同的 attention head 学到不同的衰减曲线——有的关注局部（快速衰减），有的关注全局（慢衰减）。

LLEE 的证据衰减做了完全相同的事，但用人工设定的速率：

```
ATMOSPHERIC:  0.7/turn  — 快衰减，类似局部 attention head
CONTEXTUAL:   0.9/turn  — 中衰减
EXPLICIT:     1.0/turn  — 不衰减，类似全局 attention head
CHARACTER:    1.0/turn  — 不衰减，类似 positional embedding 的常量偏置
```

这里有一个深刻的类比：

**LLEE 的 6 种证据类型，本质上是 6 个"手工设计的 attention head"。**

每个 head 有自己的衰减曲线，关注不同类型的信息。EXPLICIT head 永远记住事实，ATMOSPHERIC head 只关注当前场景的氛围。这和 Transformer 中不同 head 学到不同时间尺度的 attention pattern 是同一个设计模式。

区别在于：Transformer 的 head 是从数据中学出来的，LLEE 的 head 是从叙事学理论中设计出来的。

**这个区别是 LLEE 的核心价值所在——也是它最大的风险。**

如果人工设计的衰减曲线恰好接近"最优"，LLEE 就比端到端学习更高效（不需要海量训练数据）。如果偏离太远，LLEE 就不如让模型自己学。Phase 4 的进化实验本质上就是在回答这个问题：人工设计的 attention pattern 离最优有多远？

---

## 三、归一化 vs 独立——一个被忽视的设计选择

Token 概率是归一化的：所有 token 的概率和为 1。这意味着 token 之间互相竞争——一个 token 的概率上升，其他 token 的概率必然下降。

LLEE 的置信度不是归一化的。每个属性的 confidence 独立计算，不互相竞争。Aladdin 的 emotion.confidence = 0.8 不影响 Abanazar 的 emotion.confidence。

这个差异看起来是技术细节，但它反映了一个根本的建模选择：

```
归一化（token 模型）：
  世界是一个选择题——在所有可能的下一个 token 中选一个
  适合：语言生成（下一个词只能是一个）

独立（LLEE 模型）：
  世界是一组并行的状态——每个属性独立存在
  适合：世界状态描述（Aladdin 可以同时害怕、奔跑、在洞穴里）
```

这指向了一个更大的问题：**LLEE 的世界状态是否应该引入属性间的竞争？**

比如：一个角色不太可能同时"极度恐惧"和"极度愤怒"。如果 emotion.fear 的 confidence 很高，emotion.anger 的 confidence 应该被压低。这就是情绪空间的"softmax"——情绪之间互相竞争注意力资源。

当前 LLEE 没有这个机制。每个属性独立。这在 Phase 0 是合理的简化，但如果要建模更复杂的心理状态，可能需要引入某种形式的归一化——不是全局 softmax，而是同一语义组内的竞争。

```python
# 假设的情绪竞争机制（Phase 4+ 的可能方向）
emotion_logits = {"fear": 2.1, "anger": 1.3, "joy": -0.5}
emotion_probs = softmax(emotion_logits)
# → fear: 0.65, anger: 0.29, joy: 0.05
# 这比独立的 confidence 更接近人类情绪的互斥性
```

---

## 四、Scheme C 就是 softmax → argmax

LLEE 的 Scheme C（内部连续置信度，外部离散等级）和 LLM 的 softmax → argmax 是完全相同的操作：

```
LLM:
  连续 logits → softmax → 连续概率 → argmax → 离散 token
  内部可微      ↑ 可微      ↑ 可微      ↑ 不可微    外部离散

LLEE Scheme C:
  连续 confidence → display_level 映射 → 离散等级
  内部可微          ↑ 不可微（分段函数）    外部离散
```

LLM 用 Gumbel-Softmax 或 straight-through estimator 来让 argmax 可微。LLEE 如果要引入梯度优化，也需要类似的技巧——让 display_level 的边界可微。

具体来说，当前的 `render_intensity()` 是分段线性的：

```python
if confidence > 0.8: return 1.0
elif confidence > 0.5: return 0.3 + (confidence - 0.5) * 1.0
elif confidence > 0.3: return 0.1 + (confidence - 0.3) * 1.0
return 0.0
```

如果换成 sigmoid 的叠加，就变成可微的：

```python
def render_intensity_smooth(confidence, thresholds=[0.3, 0.5, 0.8], steepness=10):
    """可微版本的渲染强度映射。steepness 控制边界锐度。"""
    # 三个 sigmoid 的加权叠加，近似分段线性但处处可微
    s1 = sigmoid((confidence - thresholds[0]) * steepness) * 0.1
    s2 = sigmoid((confidence - thresholds[1]) * steepness) * 0.2
    s3 = sigmoid((confidence - thresholds[2]) * steepness) * 0.7
    return s1 + s2 + s3
```

这不是现在要做的事。但它说明了一个原则：**LLEE 的每一个离散设计选择，都有一个连续的、可微的对应物。** 从离散到连续的切换，就是从"人工设计"到"梯度优化"的切换。Phase 0-3 用离散版本证明框架有效，Phase 4 用连续版本证明框架可优化。

---

## 五、置信度上限就是 prior

今天加了一个代码改动：WSM 在 apply_delta 时 clamp confidence 到 `EVIDENCE_CONFIDENCE_CEILING`。

```python
EVIDENCE_CONFIDENCE_CEILING = {
    EXPLICIT:    1.0,
    BEHAVIORAL:  0.85,
    ATMOSPHERIC: 0.30,
    CONTEXTUAL:  0.50,
    CHARACTER:   0.90,
}
```

从贝叶斯的角度看，这些上限就是先验（prior）。它们编码了一个信念：**"无论文本说了什么，ATMOSPHERIC 类型的证据最多只能有 30% 的可信度。"**

这和 LLM 中的 temperature 有类似的效果——temperature 越高，概率分布越平坦，模型越"不确定"。ATMOSPHERIC 的 0.30 上限相当于说"对环境推断的情绪，永远保持高 temperature"。

但先验可以被数据更新。贝叶斯更新的公式是：

```
posterior ∝ likelihood × prior
```

LLEE 当前没有贝叶斯更新——confidence 是直接赋值的，不是从先验和似然计算出来的。如果引入贝叶斯框架：

```
# 当前：直接赋值 + clamp
confidence = min(raw_confidence, ceiling)

# 贝叶斯版本：先验 × 似然
prior = EVIDENCE_CONFIDENCE_CEILING[level]  # 先验上限
likelihood = raw_confidence                  # 来自文本的证据强度
posterior = prior * likelihood / normalizer   # 贝叶斯更新
```

这会让系统更优雅，但也更复杂。当前的 clamp 是贝叶斯更新的一个粗糙近似——它保证了后验不超过先验，但没有利用似然来精确计算后验。

**这是 Phase 4 路径 A（优化映射层参数）的一个具体方向：用梯度下降学习最优的先验分布，而不是手工设定上限。**

---

## 六、衰减就是遗忘——LLEE 和工作记忆的类比

人类的工作记忆有容量限制（Miller's 7±2）。信息如果不被复述（rehearsal），就会衰减。不同类型的信息衰减速度不同：

- 事实性知识（"巴黎是法国首都"）→ 长期记忆，不衰减
- 情景记忆（"今天早上吃了什么"）→ 中速衰减
- 感觉记忆（"刚才闻到的味道"）→ 快速衰减

LLEE 的衰减率完美映射到这个认知模型：

```
EXPLICIT (1.0)    ↔ 长期记忆中的事实
CHARACTER (1.0)   ↔ 长期记忆中的人格特质
CONTEXTUAL (0.9)  ↔ 情景记忆
ATMOSPHERIC (0.7) ↔ 感觉记忆
```

narrative_break（场景切换）对应认知心理学中的"情境模型更新"（situation model updating）——当读者感知到场景变化时，工作记忆中的情境信息被清除，为新场景腾出空间。这正是 ATMOSPHERIC → 0.0 的认知基础。

这个类比不只是修辞。它暗示了一个可测试的预测：

**如果 LLEE 的衰减率接近人类工作记忆的衰减率，那么 LLEE 的状态轨迹应该和人类读者的心理状态轨迹高度相关。**

这可以在 Phase 3 的人类评估中测试：让被试在阅读过程中标注自己对世界状态的感知，然后和 WSM 的状态轨迹做相关分析。如果相关性高，说明 LLEE 的衰减模型捕捉到了人类阅读理解的某种认知结构。

---

## 七、最深处的问题：LLEE 是一种压缩吗？

LLM 的本质是压缩——它把训练语料压缩成参数，然后通过采样"解压"出新文本。Shannon 信息论告诉我们，最优压缩等价于最优预测。

LLEE 做的事情也是压缩：把一段叙事文本压缩成一个 WorldStateDelta JSON。但这是一种非常特殊的压缩——它不是无损的（丢弃了修辞、节奏、风格），也不是为了最小化比特数，而是为了保留"可渲染的信息"。

```
LLM 压缩：
  文本 → 参数 → 文本'
  目标：最小化 KL(P_data || P_model)
  保留：统计规律

LLEE 压缩：
  文本 → WorldStateDelta → 渲染
  目标：最大化渲染忠实度
  保留：可感知的世界状态
```

这两种压缩的交汇点在哪里？

**在"什么信息值得保留"这个问题上。**

LLM 保留的是统计上频繁出现的模式。LLEE 保留的是叙事上重要的状态。两者的差异就是"统计显著性"和"叙事显著性"的差异。

一个有趣的推论：如果我们用 LLEE 的 WorldStateDelta 作为 LLM 的 prompt（这正是 Parser 在做的事），我们实际上是在告诉 LLM："忽略统计上常见但叙事上不重要的信息，只关注这些状态。" 这是一种**注意力引导**——用符号系统引导神经网络的注意力。

反过来，如果我们用 LLM 的 attention pattern 来指导 LLEE 的证据分级（Phase 4 路径 B 的预测器），我们是在用统计规律来补充人工设计的叙事规则。

**两个方向合在一起，就是 LLEE 论文 Discussion 中值得展开的核心论点：符号系统和神经网络不是竞争关系，而是互补的压缩策略。符号系统提供可解释的结构，神经网络提供统计上的最优填充。LLEE 的 Schema 是结构，LLM 的输出是填充。**

---

## 八、对计划的启发

以上思考对 LLEE 实验计划有几个具体启发：

**1. Phase 3 人类评估可以增加一个认知实验**
让被试在阅读过程中标注"你认为当前场景的氛围是什么"，然后和 WSM 的 narrative.tension 做相关分析。如果 r > 0.7，这就是 LLEE 衰减模型的认知验证——比 CLIP 分数更有说服力。

**2. Phase 4 的进化实验可以用 attention pattern 作为参照**
把 LLM 处理同一段文本时的 attention 权重提取出来，和 LLEE 的衰减曲线做对比。如果两者形状相似，说明人工设计的衰减率接近"最优"；如果差异大，进化算法应该能找到更好的衰减率。

**3. render_intensity 的可微化是 Phase 4 路径 A 的第一步**
把分段线性换成 sigmoid 叠加，就打通了从人类评分到渲染参数的梯度通路。这个改动很小（10 行代码），但它是"LLEE 框架内引入梯度下降"的关键使能步骤。

**4. 属性间竞争（情绪 softmax）是一个独立的研究方向**
当前的独立置信度模型在 Phase 0-3 够用。但如果要建模复杂心理状态（恐惧和愤怒的互斥、悲伤和怀念的共存），需要引入属性间的结构化关系。这可以是 LLEE v2 的核心改进。

**5. 贝叶斯更新可以替代 clamp**
当前的 confidence ceiling + clamp 是贝叶斯先验的粗糙近似。如果 Phase 4 的数据足够，可以学习每种证据类型的先验分布（不只是上限），然后用贝叶斯更新替代 clamp。这会让系统更优雅，也更容易和认知科学文献对接。

---

## 九、一句话

LLEE 的置信度系统和 LLM 的 token 概率不只是"看起来像"——它们是同一个问题的两种解法：**如何在不确定性下，从有限的证据中构建对世界的信念，并决定如何行动。** LLM 用梯度下降从数据中学习这个映射，LLEE 用人类知识手工设计这个映射。两者的交汇点——用数据优化人工设计的框架——正是 Phase 4 要做的事，也是 LLEE 最有理论价值的贡献。
