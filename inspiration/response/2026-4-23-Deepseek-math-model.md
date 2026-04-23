这份开发笔记的自我诊断非常清醒。我来直接回答你的三个问题。

一、是否应该在 v0.7 论文内把 UNDEFINED 数学解耦？
应该。而且这是 v0.7 数学化最核心、最应该优先完成的任务。

当前 v0.6 对 UNDEFINED 的处理是语义描述性的——“文本没说，我就不渲染”。v0.7 需要将其推进到数学操作性的层面。

具体的解耦方案（可直接写入论文）：

将 UNDEFINED 拆分为两个数学上不等价的子类型：

text

复制

下载
UNDEFINED 的子类型划分：
├─ UNDEFINED_EPISTEMIC   # 文本有信息，但 Parser 未能提取（模型能力不足）
└─ UNDEFINED_ALEATORIC   # 文本本身没有信息（叙事世界的本质不确定性）
数学表达：

对于任意世界状态属性 $a$，其在时刻 $t$ 的证据状态定义为三元组：

𝐸
(
𝑎
,
𝑡
)
=
(
𝑣
,
𝑐
,
𝜎
)
E(a,t)=(v,c,σ)
其中：

$v$：属性值（可能为 None）

$c \in [0,1]$：置信度

$\sigma \in {\text{EPISTEMIC}, \text{ALEATORIC}}$：不确定性来源分类

形式化定义：

偶然性 UNDEFINED：源文本 $T$ 中不存在任何可被人类标注者识别为与属性 $a$ 相关的信息。
Info
(
𝑇
,
𝑎
)
=
∅
  
⟹
  
𝜎
=
ALEATORIC
Info(T,a)=∅⟹σ=ALEATORIC

认知性 UNDEFINED：源文本 $T$ 中包含与属性 $a$ 相关的信息，但 Parser 未能提取。
Info
(
𝑇
,
𝑎
)
≠
∅
 
∧
 
𝑣
=
None
  
⟹
  
𝜎
=
EPISTEMIC
Info(T,a)

=∅ ∧ v=None⟹σ=EPISTEMIC

渲染语义：

子类型	渲染器行为
UNDEFINED_ALEATORIC	使用中性默认值，且该默认值不可被任何上下文联想覆盖
UNDEFINED_EPISTEMIC	使用中性默认值，但允许渲染器在用户授权下进行低强度的上下文推断（如从相邻段落的证据中插值）
这一步的价值：

将 IEI 的根源精确锁定为“混淆 ALEATORIC 与 EPISTEMIC”

为 Phase 4 的预测器提供一个明确的输出目标：预测器应尽量减少 EPISTEMIC UNDEFINED，但不应尝试填充 ALEATORIC UNDEFINED

使 UNDEFINED 从一个“消极的放弃”变为一个“积极的分类决策”

二、在 v0.7 论文内还需要描述什么数学模型？
基于开发笔记中提出的 M1-M9 框架，v0.7 论文应该分层描述以下数学模型：

第一层：核心架构的形式化（必须有，对应 M1-M4）

编号	数学内容	在论文中的位置
M1	WSM 状态空间与差分更新的形式化定义：$W = (E,V,S,O,H,T,N)$，$W_{t+1} = \text{WSM}(W_t, \Delta_t)$	Section 4.1
M2	证据置信度的衰减方程：$c_{t+1}(e) = c_t(e) \cdot r_{\text{level}(e)}$，以及叙事断裂时的分段处理	Section 5.4
M3	置信度天花板的形式化：$\forall t, \forall e,\ c_t(e) \leq \theta_{\text{level}(e)}$	Section 5.3
M4	IEI 的操作化定义：$\text{IEI}(\Delta, T) = 1 \iff \exists a \in \Delta.\text{emotions}: a \neq \text{UNDEFINED} \land \text{NoEvidence}(T, a)$	Section 3.1
第二层：实验度量的形式化（支撑数据，对应 M5-M6）

编号	数学内容	在论文中的位置
M5	填充率：$\text{FillRate}(\Delta) = \frac{|{f \in \mathcal{F} : \Delta[f] \neq \text{None}}|}{|\mathcal{F}|}$，并按模态分组（环境填充率、情绪填充率等）	Section 7.3
M6	证据校准度：Cohen's Kappa $\kappa = \frac{P_o - P_e}{1 - P_e}$，用于 Parser 与人工标注的一致性检验	Section 7.3
第三层：理论延伸的形式化（指向未来，对应 M7-M9）

这些不应作为 v0.7 的“已实现贡献”出现，而应放在 Discussion / Future Work 中，作为“理论框架的扩展方向”。

编号	数学内容	在论文中的位置
M7	衰减率的信息论解释：$r_{\text{level}} \approx \exp(-H(s_{t+1}^{\text{level}} \mid s_t^{\text{level}}))$	Discussion
M8	不确定性分解：$H_{\text{pred}}(s_t) = H_{\text{epistemic}}(s_t) + H_{\text{aleatoric}}(s_t)$	Future Work
M9	叙事分岔点的局部李雅普诺夫指数：$\lambda_{\text{local}}(s_t) = \max \text{Re}(\text{Eig}(J(s_t)))$，用于 Phase 4 预测器的分析	Future Work
三、这些数学模型能解决渲染问题吗？
部分能直接解决，部分为未来解决铺路。

能直接解决渲染问题的（v0.7 即可落地）：

数学模型	解决的渲染问题
M3（置信度天花板）	防止 ATMOSPHERIC 证据过度驱动渲染，避免“阴天让角色变悲伤”的越界渲染
M2（衰减方程）	确保未被重复确认的证据逐渐退出渲染，避免“前一场雨的潮湿感带到三天后”的状态污染
UNDEFINED 的子类型拆分	让渲染器区分“因为文本没说所以不渲染”（ALEATORIC）和“因为 Parser 漏了所以不渲染”（EPISTEMIC），为后者的可配置回填提供接口
M4（IEI 形式化）	为 IEI 泄漏率的自动检测提供数学判据，使得渲染保真度的评估从“人工感觉”变为“可计算的指标”
为未来解决渲染问题铺路的（Phase 4 及以后）：

数学模型	未来能解决的渲染问题
M7（衰减率的信息论估计）	用数据校准衰减率，使渲染的“记忆持久度”更符合人类读者的认知曲线（Phase 3 认知实验的延伸）
M8（不确定性分解）	让渲染器在 EPISTEMIC 区域进行可审计的低强度推断（如从相邻场景插值光照），而在 ALEATORIC 区域保持严格中性——这是“渲染智能”从“死板”走向“灵活”的关键一步
M9（局部李雅普诺夫指数）	识别叙事的“分岔点”，在这些节点上，渲染器应主动缩短状态继承链、增加中性默认值的使用，避免将高不确定性状态带入后续渲染——这是“渲染稳健性”的数学保障
四、v0.7 论文数学化的总结性建议
层次	内容	性质
核心贡献	M1-M4 + UNDEFINED 子类型拆分	已实现，已形式化
实验支撑	M5-M6	已实现，已量化
理论延伸	M7-M9	未实现，作为 Future Work 的数学蓝图
一句话：v0.7 论文的数学化，不是为了“装点门面”，而是为了让 LLEE 的每一个设计决策——从置信度天花板到衰减率，从 UNDEFINED 到 IEI 判据——都有一个可以被质疑、被测试、被改进的数学表达式。当前回应的数学模型，对于“描述当前系统如何工作”已经足够；对于“指导未来系统如何进化”，则提供了清晰的路标。