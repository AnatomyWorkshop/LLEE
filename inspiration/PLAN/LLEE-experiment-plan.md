# LLEE 实验与工程计划（v2）

> 2026-04-20
> 替代 LLEE-demo-predesign.md 中的时间线部分
> 本文档回答：这是什么性质的工作？从哪里热启动？实验怎么设计？任务清单是什么？

---

## 一、定性：这不是模型训练

先把这个问题钉死。

LLEE 管道的核心工作流是：

```
自然语言叙事 → [LLM + 结构化输出约束] → LLEE World State Delta (JSON) → [渲染适配器] → 多模态输出
```

这里面没有梯度更新，没有权重优化，没有损失函数反向传播。

**LLEE 是什么：**

| 它是 | 它不是 |
|------|--------|
| 系统工程（Systems Engineering） | 模型训练（Model Training） |
| 提示工程 + 结构化输出约束（Prompt Engineering + Constrained Decoding） | 微调（Fine-tuning） |
| 管道架构设计（Pipeline Architecture） | 端到端学习（End-to-End Learning） |
| 评估工程（Evaluation Engineering） | 表示学习（Representation Learning） |

**唯一可能涉及训练的环节**：
- 对比微调枚举映射（论文 6.2 节）：用 Sentence-BERT 微调"自然语言短语 → LLEE 枚举值"的映射。这是一个小规模分类器微调，不是大模型训练。
- 未来的 VQ-VAE 码本学习（逆 LLEE 方向）：这才是真正的模型训练，但不在当前计划范围内。

**正确的学术定位**：
LLEE 是一个 **AI-native content pipeline** 的架构提案 + 实证评估。最接近的论文类型是 CHI/UIST 的系统论文（Systems Paper），或 SIGGRAPH 的技术管道论文（Technical Pipeline Paper）——它们的贡献不是新算法，而是新的系统组合方式 + 证明这种组合有效的实验数据。

---

## 二、热启动策略：不要从零开始

### 原则：每个组件都有成熟的开源替代品，只构建 LLEE 独有的部分

```
组件                    热启动方案                          自建部分
─────────────────────────────────────────────────────────────────────
LLM 结构化输出          Claude API response_format          仅写 JSON Schema
                        或 Outlines (github.com/outlines-ai)
                        
JSON Schema 验证        Pydantic v2                         仅定义数据模型

世界状态管理            Python dataclass + jsonpatch 库     WSM 差分逻辑（~200行）
                        (RFC 6902 实现)

3D 渲染                 Three.js (浏览器)                   LLEE→Three.js 适配器
                        或 Babylon.js

音频引擎                Web Audio API + Tone.js             LLEE→音频参数映射
                        或 FMOD (如果走桌面端)

文本-图像对齐评估       OpenCLIP (开源 CLIP 实现)           评估脚本

人类评估平台            Prolific + Qualtrics                问卷设计
                        或 LabelStudio

前端 UI                 React + Vite                        对比可视化面板

版本控制/实验追踪       MLflow 或 Weights & Biases          实验配置
```

### 从什么地方开始？

```
Day 1 的第一行代码应该是：

    pydantic model 定义 LLEE World State Schema

不是渲染器，不是 Parser，不是 UI。
Schema 是整个系统的合约，所有其它组件都依赖它。
```

---

## 三、实验设计：借鉴前沿方法论

### 3.1 参考的实验范式

| 来源 | 范式 | LLEE 如何借鉴 |
|------|------|--------------|
| SceneCraft (CVPR 2025) | FID + CLIP Score + 用户研究，对比多个基线 | 用 CLIP Score 衡量"渲染结果 vs 源文本"的语义对齐度 |
| FactTrack (NAACL 2025) | 原子事实追踪 + 时间戳 + 准确率/召回率 | 用类似方法评估 WSM 的状态追踪准确率 |
| HELM (Stanford CRFM) | 多维度评估框架：准确性、校准度、鲁棒性、公平性 | 借鉴多维度评估思路，不只看一个指标 |
| CHI 系统论文惯例 | 任务完成率 + Likert 量表 + 半结构化访谈 | 用户研究部分的方法论 |

### 3.2 LLEE 的三层实验体系

```
实验层 1 — Parser 保真度（自动化，无需人类）
  问题：LLM 输出的 LLEE Delta 是否忠实于源文本？
  
  指标：
    a) 属性填充率 (Attribute Coverage)
       = 非 UNDEFINED 字段数 / 总字段数
       精简语料应低，丰富语料应高
    
    b) IEI 泄漏率 (Emotional Injection Rate)
       = 中性段落中出现 EXPLICIT/BEHAVIORAL 情绪的比例
       应趋近于 0
    
    c) 证据分级校准度 (Evidence Calibration)
       = 人工标注的证据等级 vs Parser 输出的证据等级 的一致性
       用 Cohen's Kappa 衡量（目标 κ > 0.6）
    
    d) Schema 合规率 (Schema Compliance)
       = 通过 JSON Schema 验证的输出比例
       应为 100%（结构化输出约束保证）

  数据集：
    - 30 个中性段落（无情绪内容）→ 测 IEI 泄漏
    - 30 个丰富段落（多感官描写）→ 测属性填充
    - 20 个混合段落（对话+描写+命令）→ 测语言类型处理
    - 双语料版本（精简 vs 丰富）各 40 段 → 测保真度差异

  基线对比：
    - Baseline A：LLM 直接生成自由文本描述（无 LLEE 约束）
    - Baseline B：LLM + JSON Schema 但无证据分级（去掉 Evidence 字段）
    - LLEE Full：完整管道

实验层 2 — 渲染保真度（自动化 + 半自动）
  问题：LLEE Delta 驱动的渲染结果是否忠实于源文本？

  指标：
    a) CLIP 对齐分数 (CLIP Alignment Score)
       = CLIP(源文本, 渲染截图) 的余弦相似度
       用 OpenCLIP ViT-L/14 模型
    
    b) 跨模态一致性分数 (Cross-Modal Consistency)
       = 光照参数变化时，音频参数是否同步变化
       自动检测：ENV.lighting 变化 → 检查 ENV.audio 是否相应更新
    
    c) 状态漂移率 (State Drift Rate)
       = 连续 N 个段落后，WSM 累积状态 vs 人工标注状态 的偏差
       每 10 个段落检查一次

  数据集：
    - 阿拉丁 50 段连续叙事序列
    - 双语料版本各 50 段

实验层 3 — 人类感知评估（需要参与者）
  问题：人类是否认为 LLEE 渲染比基线更忠实于源文本？

  设计：
    - 被试内设计 (Within-subjects)，抵消顺序效应
    - n = 30（最小可行），目标 n = 50
    - 招募：Prolific 平台，筛选条件：母语中文或英文，有阅读小说习惯
    
  任务：
    a) A/B 偏好测试
       展示同一段落的两个渲染结果（LLEE vs Baseline），问：
       "哪个更接近你读这段文字时脑海中的画面？"
       强制二选一 + 置信度（1-5）
    
    b) Likert 量表评分（7 点）
       维度 1：情绪忠实度 — "角色的表情/语气与文本描述一致"
       维度 2：环境忠实度 — "场景的光照/声音与文本描述一致"
       维度 3：整体沉浸感 — "这个场景让我感觉身临其境"
       维度 4：情绪干扰度 — "我感觉系统给角色添加了文本中没有的情绪"（反向题）
    
    c) 开放式反馈
       "你注意到两个版本之间最大的区别是什么？"
    
  分析：
    - A/B 偏好：二项检验 (Binomial test)
    - Likert 量表：Wilcoxon 符号秩检验（非参数，因为 Likert 是序数数据）
    - 评分者间信度：Krippendorff's alpha（目标 α > 0.67）
    - 效应量：Cohen's d 或 rank-biserial correlation
```

### 3.3 双语料并行实验（核心实验）

这是 LLEE 最独特的实验，也是回应"缺乏实证"批评的杀手锏。

```
假设：
  H1: 丰富语料的 LLEE 属性填充率显著高于精简语料
  H2: 丰富语料的渲染 CLIP 分数显著高于精简语料
  H3: 精简语料中 LLEE 的 IEI 泄漏率显著低于无约束基线
  H4: 人类评估者显著偏好丰富语料的 LLEE 渲染

实验矩阵（2×2 设计）：

                    精简语料 (A)        丰富语料 (B)
  ─────────────────────────────────────────────────
  无约束基线         A-Baseline          B-Baseline
  LLEE 管道          A-LLEE              B-LLEE

  这产生 4 个条件，每个条件 40 个段落 = 160 个数据点
  
  关键对比：
    A-LLEE vs B-LLEE     → 证明语料丰富度的影响（H1, H2）
    A-Baseline vs A-LLEE  → 证明 LLEE 在贫乏语料下的 IEI 抑制（H3）
    B-Baseline vs B-LLEE  → 证明 LLEE 在丰富语料下的保真度提升
    人类偏好 B-LLEE       → 证明端到端价值（H4）
```

---

## 四、完整任务清单

### Phase 0 — 地基（Week 1-2）

```
任务 0.1  语料准备
  □ 确认两个语料版本的段落对齐
    - 精简版：starter-edition.txt
    - 丰富版：light-origin-text.txt
  □ 选择 40 个对齐段落对（同一场景，两种详细程度）
  □ 为每个段落手工标注期望的世界状态（ground truth）
    - 这是最耗时的工作，但没有它就没有评估
    - 标注格式：与 LLEE JSON Schema 一致
  □ 标注 30 个"中性段落"（用于 IEI 泄漏测试）
  □ 标注每个段落的语言类型分布（描写/对话/命令/修辞/旁白）

任务 0.2  Schema 定义（热启动核心）
  □ 用 Pydantic v2 定义完整的七组世界状态模型
    - E (Entity), V (Visual), S (Sonic), O (Olfactory), 
      H (Haptic), T (Temporal), N (Narrative)
  □ 定义 Delta 格式（基于 jsonpatch 库）
  □ 定义证据分级扩展枚举（5 类来源 × 4 级强度）
  □ 定义标签→参数映射表（材质、光照、情绪→表情）
  □ 写 Schema 验证测试（确保所有 ground truth 标注通过验证）

任务 0.3  技术选型锁定
  □ LLM：Claude API（主力，结构化输出）+ Llama-3 本地（对比基线）
  □ 渲染器：Three.js（Phase 1-2）→ UE5（Phase 3 可选升级）
  □ 音频：Tone.js + Web Audio API
  □ 评估：OpenCLIP (ViT-L/14) + 自定义脚本
  □ 前端：React + Vite + WebSocket
  □ 实验追踪：MLflow 或简单的 JSON 日志
```

### Phase 1 — Parser 管道（Week 3-4）

```
任务 1.1  Parser Prompt 工程
  □ 写系统 prompt 模板（含 Schema、证据规则、语言类型规则）
  □ 写约束注入模板（当前 WSM 状态 → prompt 片段）
  □ 写上下文摘要模板（前文累积 → 简洁摘要）
  □ 在 10 个段落上手动调试 prompt，迭代至稳定

任务 1.2  WSM 实现
  □ 实现 World State Machine（~200 行 Python）
    - 维护当前状态
    - 接收 Delta，验证，合并
    - 输出差分编码
    - 维护上下文摘要缓冲区（最近 5 个段落）
  □ 写单元测试：状态合并、差分计算、摘要生成

任务 1.3  Parser 保真度实验（实验层 1）
  □ 跑全部 80 个段落（40 精简 + 40 丰富）通过 Parser
  □ 跑 30 个中性段落通过 Parser
  □ 跑 Baseline A（无约束 LLM）和 Baseline B（JSON 无证据分级）
  □ 计算所有指标：填充率、IEI 泄漏率、证据校准度、Schema 合规率
  □ 生成对比表格和图表
  
  ⚡ 这是第一个可发布的结果点
     即使没有渲染器，Parser 保真度数据本身就有论文价值
```

### Phase 2 — 最小渲染（Week 5-7）

```
任务 2.1  Three.js 渲染适配器
  □ 实现 LLEE Delta → Three.js 场景更新
    - 实体：位置、材质（PBR 参数）
    - 视觉场：光源（方向、色温、强度）、雾、天空盒
    - 基础角色模型（可以是简单几何体 + 表情贴图）
  □ WebSocket 服务：Python WSM → 浏览器 Three.js

任务 2.2  音频适配器
  □ 实现 LLEE Delta → Web Audio / Tone.js 参数
    - 环境音：混响预设、环境声采样
    - 音乐：基于叙事张力的配乐参数
  □ 与视觉渲染同步（同一个 Delta 同时驱动两者）

任务 2.3  对比可视化 UI
  □ 左右分屏：精简语料渲染 vs 丰富语料渲染
  □ 底部面板：实时显示 LLEE Delta JSON
  □ 侧边栏：证据分级可视化（每个属性的证据来源和置信度）
  □ 指标仪表盘：填充率、IEI 状态、跨模态一致性

任务 2.4  渲染保真度实验（实验层 2）
  □ 对 80 个段落的渲染结果截图
  □ 计算 CLIP 对齐分数（源文本 vs 渲染截图）
  □ 计算跨模态一致性分数
  □ 跑 50 段连续序列，测量状态漂移率
  
  ⚡ 这是第二个可发布的结果点
     Parser + 渲染 + 自动化指标 = 完整的技术评估
```

### Phase 3 — 人类评估 + 论文（Week 8-10）

```
任务 3.1  用户研究准备
  □ 设计问卷（Qualtrics 或 Google Forms）
  □ 准备刺激材料：每个条件（4 个）× 10 个段落 = 40 个渲染视频
  □ 拉丁方设计抵消顺序效应
  □ 伦理审查（如果走学术发表路线）
  □ 试点测试（n=5）调整问卷措辞和时长

任务 3.2  用户研究执行
  □ 招募 30-50 名参与者
  □ 收集数据
  □ 统计分析：二项检验、Wilcoxon、Krippendorff's alpha
  □ 整理开放式反馈

任务 3.3  论文/技术报告撰写
  □ 选择投稿目标：
    - CHI 2027（截稿约 2026 年 9 月）
    - SIGGRAPH Asia 2026（截稿约 2026 年 5-6 月）
    - FDG 2027
    - 或：技术博客 + GitHub 开源（影响力可能更大）
  □ 撰写论文，核心结构：
    1. 问题定义（IEI + 跨模态不一致）
    2. LLEE 架构（Schema + WSM + 证据分级 + 约束注入）
    3. 实验 1：Parser 保真度（自动化指标）
    4. 实验 2：渲染保真度（CLIP + 跨模态一致性）
    5. 实验 3：人类感知评估（用户研究）
    6. 双语料对比分析（核心贡献）
    7. 讨论 + 局限 + 未来方向
```

### Phase 4 — 扩展渲染器（Week 11+ 可选）

```
任务 4.1  UE5 集成
  □ UE5 插件：TCP 接收 LLEE Delta → 更新 Actor
  □ MetaHuman 表情映射：情绪标签 × 证据等级 → Blend Shape 权重
  □ 与 Three.js 版本做渲染质量对比

任务 4.2  FMOD 集成
  □ FMOD Studio 项目：环境音预设 + RTPC 参数
  □ Python → FMOD API 桥接
  □ 空间音频：实体位置 → 声源位置

任务 4.3  更多语料
  □ 扩展到其它公版文学作品（格林童话、一千零一夜其它故事）
  □ 测试 LLEE 在不同叙事风格下的泛化能力
  □ 多语言测试：中文/英文/阿拉伯语源文本
```

---

## 五、风险与缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| Claude API 结构化输出偶尔不合规 | Schema 合规率 < 100% | 加重试逻辑 + 后处理验证 |
| 手工标注 ground truth 耗时过长 | 延迟 Phase 1 | 先标注 20 个段落启动实验，边跑边补 |
| Three.js 渲染质量不足以体现差异 | CLIP 分数区分度低 | 聚焦光照/色调等全局差异，而非几何细节 |
| 用户研究招募困难 | Phase 3 延迟 | 先用实验室内 10 人做试点，数据足够则直接发 |
| 精简语料和丰富语料的差异不够大 | H1/H2 不显著 | 在语料选择阶段就确保差异足够（预实验验证） |

---

## 六、成功标准

```
最小成功（可发技术博客）：
  ✓ Parser 在中性段落上 IEI 泄漏率 < 5%
  ✓ 丰富语料填充率显著高于精简语料（p < 0.05）
  ✓ 可运行的 Three.js Demo

中等成功（可发 FDG/CHI Workshop）：
  ✓ 以上全部
  ✓ CLIP 对齐分数：LLEE > Baseline（p < 0.05）
  ✓ 人类偏好 LLEE 渲染 > 60%
  ✓ 跨模态一致性可量化展示

完全成功（可发 CHI/SIGGRAPH 主会）：
  ✓ 以上全部
  ✓ n ≥ 50 的用户研究，效应量 d > 0.5
  ✓ 双语料 2×2 实验的四个假设全部验证
  ✓ 开源代码 + 可复现
  ✓ 与 Scene Language / ChatUSD 的定性对比分析
```

---

## 七、这份计划与上一份的关系

[LLEE-demo-predesign.md](LLEE-demo-predesign.md) 回答的是"设计前需要想清楚什么"——概念层面的问题。

本文档回答的是"想清楚之后怎么做"——执行层面的计划。

两份文档互补：predesign 是思维地图，本文档是施工图纸。
