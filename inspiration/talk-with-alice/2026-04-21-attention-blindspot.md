# LLM 注意力盲区与 LLEE 世界切片的完整性问题

> 2026-04-21
> 回应 D:\LLEE\inspiration\response\LLEE-environment.txt
> 核心问题：LLM 的注意力机制天然忽略"世界切片尽可能全"的信息，LLEE 在设计时是否会遇到同样的问题？

---

## 一、LLM 的注意力盲区是什么

LLM 处理叙事文本时，attention 分布是不均匀的。实验观察到的规律：

```
高 attention 区域：
  - 角色名字、对话内容、动作动词
  - 情绪词（"afraid", "angry", "joyful"）
  - 叙事转折标记（"suddenly", "but", "however"）

低 attention 区域：
  - 环境描写中的物理细节（材质、温度、湿度）
  - 空间关系（"左边"、"远处"、"头顶"）
  - 声学信息（混响、环境音、静默）
  - 持续性状态（光照没变、角色还站在原地）
```

这不是 bug，是 feature——LLM 被训练来预测下一个 token，而叙事推进主要靠角色和事件，不靠环境细节。环境描写在统计上是"低信息量"的（对预测下一个 token 贡献小），所以 attention 自然低。

**但对渲染来说，这些"低 attention"的信息恰恰是最重要的。** 渲染器需要知道光从哪里来、墙是什么材质、空间有多大——这些是画面的 80%，角色只占 20%。

---

## 二、LLEE 是否会遇到同样的问题？

**会。而且已经在遇到了。**

LLEE 的 Parser 是一个 LLM（Claude API）。当它解析叙事文本时，它继承了 LLM 的 attention 偏好：

```
Parser 容易提取的：
  - entity.emotion（情绪词 attention 高）
  - entity.action（动作动词 attention 高）
  - narrative.tension（叙事转折 attention 高）

Parser 容易遗漏的：
  - visual.lights（光照描写通常是从句或修饰语，attention 低）
  - visual.atmosphere.fog_density（"雾气弥漫"可能被当作修辞而非物理事实）
  - sonic.ambient_sounds（"滴水声"在叙事中是背景，attention 低）
  - haptic.temperature（"寒冷"可能被归为情绪而非触觉）
  - 空间关系（"站在入口处"的位置信息容易被忽略）
```

这意味着 LLEE 的 WorldStateDelta 会系统性地偏向"角色+情绪"，而偏离"环境+物理"。渲染出来的世界会是：角色情绪丰富，但站在一个空白的、缺少细节的空间里。

**这正是你说的"世界切片不够全"的问题。**

---

## 三、LLEE-environment.txt 的分析价值

这篇文档提出了 9 个方向的质疑，其中对当前工程最有直接价值的是：

**问题六（具身认知）和环境三层分离架构。**

文档提出的 L1/L2/L3 三层分离：

```
L1 语义锚点：文本明确提及的环境事实 → 进入 LLEE 块
L2 空间骨架：区域划分、实体位置关系 → 进入 LLEE 块
L3 资产填充：具体 3D 模型、纹理、音效 → 渲染器本地映射
```

这个架构是对的。但它暴露了当前 schema 的一个缺陷：**VisualField 没有 features 字段。**

当前的 `scene_type: "cave_interior"` 是一个粗粒度标签。文档正确指出，"cave" 可以是溶洞、矿洞、墓穴——视觉差异巨大。文本中的 "stalactite"、"dripping water"、"fissure light" 这些具体特征，在当前 schema 中无处安放。

同样，`HapticField` 有 temperature 和 humidity，但它们是占位符，Parser prompt 里没有要求提取它们。

---

## 四、注意力盲区的对策

### 对策 1：在 Parser prompt 中显式要求环境提取

当前 prompt 的 Critical Rules 聚焦于证据分级和 ATMOSPHERIC 约束。需要增加一条：

```
6. ENVIRONMENT EXTRACTION: For every passage, actively scan for:
   - Light sources and their properties (direction, color, intensity)
   - Spatial features mentioned in text (stalactites, windows, furniture)
   - Acoustic cues (silence, echoes, specific sounds)
   - Tactile/atmospheric cues (temperature, humidity, wind)
   Even if these seem like "background" details, they are critical for rendering.
```

这条规则的作用是**对抗 LLM 的 attention 偏好**——强制它关注通常被忽略的环境信息。

### 对策 2：在 VisualField 中增加 scene_features

```python
class VisualField(BaseModel):
    lights: list[LightSource] = Field(default_factory=list)
    atmosphere: VisualAtmosphere = Field(default_factory=VisualAtmosphere)
    scene_type: Optional[str] = None
    scene_type_evidence: Evidence = Field(default_factory=Evidence)
    scene_features: list[str] = Field(default_factory=list)  # NEW
```

`scene_features` 是文本中明确提及的环境特征标签列表。例如：

```json
{
  "scene_type": "cave_interior",
  "scene_features": ["stalactite", "dripping_water", "fissure_light", "stone_floor"]
}
```

渲染器拿到 features 后，通过确定性映射激活对应的资产模块。这不是"联想"，是"展开"——标签到资产的映射是预定义的。

### 对策 3：后处理验证器检查填充率

在 stability_test 中增加一个指标：**环境填充率**。

```
环境填充率 = (非 None 的环境字段数) / (总环境字段数)

目标：丰富语料（Poe）的环境填充率 > 60%
      稀疏语料（Aladdin）的环境填充率 > 20%
```

如果 Parser 系统性地遗漏环境信息，这个指标会暴露问题。

---

## 五、更深的问题：UNDEFINED 是信息还是噪声？

LLEE-environment.txt 中有一个关键立场：**UNDEFINED 就是 UNDEFINED，渲染器不得联想填充。**

这个立场在 Zero-Introspection 原则下是正确的。但它引出了一个微妙的问题：

**当 Parser 因为 attention 盲区而遗漏了文本中实际存在的环境信息时，产生的 UNDEFINED 不是"真正的无信息"，而是"Parser 的失误"。**

```
真正的 UNDEFINED：文本确实没有描述这个属性
  → 渲染器应该用中性默认值

虚假的 UNDEFINED：文本描述了，但 Parser 没提取到
  → 渲染器用中性默认值 = 信息丢失
```

这两种 UNDEFINED 在当前系统中无法区分。Phase 1 的保真度实验可以量化这个问题：对比 ground truth 标注和 Parser 输出，统计"虚假 UNDEFINED"的比例。

如果虚假 UNDEFINED 比例高（>15%），说明 attention 盲区是一个真实的工程问题，需要更激进的 prompt 工程或后处理补全。

---

## 六、"事实陈述原则"与 attention 盲区的张力

LLEE-environment.txt 提出了一个优雅的架构原则：**状态只来自因（文本事实），不来自果（角色认知）。** 渲染器负责"语气"，LLEE 负责"事实"。

这个原则是对的。但 attention 盲区制造了一个实际困难：

**如果 Parser 因为 attention 偏好而系统性地遗漏环境事实，那么 LLEE 传递给渲染器的"事实"就是不完整的。渲染器拿到的不是"世界的全部事实"，而是"LLM 注意到的那部分事实"。**

这不是 LLEE 架构的问题，是 LLM 作为 Parser 的固有局限。对策：

1. **prompt 层面**：显式要求环境提取（对策 1）
2. **schema 层面**：提供更细粒度的环境字段（对策 2），让 Parser 有"地方放"这些信息
3. **验证层面**：用填充率指标监控遗漏（对策 3）
4. **Phase 4 层面**：用上下文预测器补全 Parser 遗漏的环境信息（PREDICTED 级别证据，置信度上限 0.4）

第 4 点特别有意思——它把 attention 盲区变成了上下文预测器的训练信号。预测器学到的就是"LLM 通常会忽略什么"，然后补上。

---

## 七、对问题七（多视角）的回应

LLEE-environment.txt 中关于"状态只来自因"的讨论非常清晰。当前 schema 的 `NarrativeMeta.focus_entity` 已经提供了一个轻量的视角提示，不需要建模多视角世界状态。

但有一个值得注意的边界情况：**不可靠叙述者。**

当叙述者说"I felt calm"但实际在撒谎时，这条 EXPLICIT 证据是"文本事实"（叙述者确实说了），但不是"世界事实"（叙述者并不 calm）。

当前 schema 没有区分这两者。LLEE-environment.txt 提出用 `source` 字段标注叙述者可信度——这和开发日志中提到的 UNRELIABLE 证据类型是同一个方向。

**建议：不在 Phase 0-3 实现，但在论文 Limitations 中明确声明这个边界。** 当前系统假设叙述者可信。处理不可靠叙述需要跨段落的推理（后来的文本推翻前面的陈述），这超出了单段落 Parser 的能力。

---

## 八、对计划的具体建议

### 纳入 Phase 0（立即可做）

1. **schema.py**：VisualField 增加 `scene_features: list[str]`
2. **parser_prompt.py**：增加环境提取规则（Critical Rule #6）
3. **stability_test.py**：增加环境填充率指标

### 纳入 Phase 1（保真度实验）

4. 统计"虚假 UNDEFINED"比例——Parser 遗漏了文本中实际存在的环境信息的频率
5. 对比有/无环境提取规则的 prompt 版本，量化 attention 盲区对策的效果

### 纳入 Phase 4（远期）

6. 上下文预测器的训练目标之一：补全 Parser 的环境信息遗漏
7. 进化算法的适应度函数增加"环境填充率"权重

### 纳入论文

8. Discussion：LLM attention 偏好与世界状态完整性的张力
9. Limitations：当前系统假设叙述者可信；环境信息提取受 LLM attention 分布限制
10. Future Work：空间骨架（@REGION）、环境特征系统、不可靠叙述支持
