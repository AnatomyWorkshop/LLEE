# LLEE 开发笔记——文本选取与渲染器规划
> 2026-04-20
> 对应：LLEE-vs-Omniverse-Analysis.md 思路 + 文本选取 + 渲染器问题

---

## 一、文本选取规划
### 现有文本概况
| 文本 | 规模 | 风格 | 感官密度 |
|------|------|------|----------|
| Aladdin starter-edition | 51 行 | 精简童话叙事 | 低 |
| Aladdin light-origin | 235 行 | 叙事大纲 | 中 |
| Roger Ackroyd (Christie) | 10545 行 | 对话主导、室内场景 | 低～中 |
| Poe Vol.2 | 21047 行 | 极端氛围描写 | 极高 |

### 选取策略
**不将 Aladdin light-origin 作为“丰富文本”**——它仍属于情节级叙事，而非场景级描写。真正意义上的“丰富文本”是 Poe 作品。

**双文本对照最优组合**：
```
极简文本组(A)：
  Aladdin starter-edition + Roger Ackroyd 对话场景
  特点：动作驱动、对话主导、环境描写极少
  代表段落：
  - Aladdin 洞穴入口（7 词，纯动作）
  - Ackroyd 晨间对话（6 词，纯对话、情绪中性）
  - Aladdin 神灯触摸（6 词，动作+对话）

丰富文本组(B)：
  Poe 作品《House of Usher》+《Masque of the Red Death》
  特点：感官密集、氛围渲染、视觉/听觉/触觉全面覆盖
  代表段落：
  - Usher 临近场景（11 词，极端哥特氛围）
  - Masque 七间房描写（23 词，纯视觉、色彩/光线/材质）
  - Pit and Pendulum（备选，极端感官剥夺与过载切换）
```

### 为什么 Poe 是最佳“丰富文本”
Poe 的文本对 LLEE 构成一套完整极限测试：
1. **视觉场（V）**：七间房间各有明确色彩、光照、材质，LLEE 的 V 组应能完整填充
2. **声场（S）**：Usher 的 *soundless day* 是明确声学状态（绝对寂静）
3. **触觉场（H）**：Usher 的 iciness、sinking 是身体感受，属于 BEHAVIORAL 级情绪证据，而非 EXPLICIT
4. **叙事张力（N）**：Poe 叙事张力极高，N.tension 应接近 1.0

**关键测试点**：
Poe 第一人称叙述者写道
> *a sense of insufferable gloom pervaded my spirit*

这是 **EXPLICIT 情绪证据**（叙述者直接陈述内心状态），LLEE 应正确标注为 EXPLICIT 而非 UNDEFINED。
它与 Aladdin 中的 *crying and lamenting* 形成对照：两者同为 EXPLICIT，但一个是内心独白，一个是行为表现。

### 侦探小说的特殊价值（对应 LLEE-vs-Omniverse-Analysis.md）
Omniverse 分析文章提出了一个高质量思路：
**用探案游戏场景作为 LLEE 的极限测试**

这一思路的价值在于：
- 侦探场景中，“证据”本身就是叙事核心机制，而非 LLEE 的技术概念
- Roger Ackroyd 的叙述者 Dr. Sheppard 本身是不可靠叙述者：陈述有真有假、有事实有推测
- LLEE 的证据分级体系可以直接映射到“这句话是事实/推断/谎言”的游戏机制
- 让 Demo 本身成为 LLEE 核心价值的展示，而非单纯技术演示

**典型场景设计**：
```
玩家看到 Dr. Sheppard 的叙述：
"Mrs. Ferrars died on the night of the 16th–17th September."
LLEE 标注：state=DECEASED, evidence=EXPLICIT（叙述者直接陈述）

玩家看到 Caroline 的推断：
"his wife poisoned him"
LLEE 标注：cause=poisoning, evidence=CONTEXTUAL（无直接证据，仅推测）

玩家看到 Sheppard 的内心活动：
"I was considerably upset and worried"
LLEE 标注：emotion=anxious, evidence=EXPLICIT（内心独白）

游戏机制：玩家可查看每个场景元素的证据等级，判断哪些是可信线索
```

这比阿拉丁密室更有说服力，因为它把 LLEE 的技术特性变成了游戏的核心玩法。

---

## 二、渲染器规划
### 需求定位：需要什么样的渲染器？
**短期（Phase 2 Demo 阶段）：Three.js 足够，但存在关键限制**

Three.js 能做好的部分：
- 光照（方向光、点光源、环境光、色温）
- 色调/氛围（后处理：色彩分级、胶片效、景深）
- 空间几何（密室/室内/室外基础形状）
- 粒子（烟雾、雨、火光）

Three.js 难以做好的部分：
- Poe 七间房的彩色玻璃窗：需要透射与染色光照，Three.js 可实现但需 Shader 工作
- Usher 黑色哥特天花板的材质质感：PBR 材质在低多边形上表现不明显
- 角色面部表情：暂不实现，使用镜头替代

**中期（Phase 4 扩展阶段）：两条路线**

路线 A：升级到 UE5
- 优点：MetaHuman 表情、Lumen 全局光照、Nanite 几何细节
- 缺点：开发成本高，需要 C++ 插件
- 适用：目标为 SIGGRAPH 或完整级 Demo

路线 B：保留 Three.js + 接入 Omniverse
- 优点：LLEE 作为 Omniverse 的 AI 前端，契合论文定位
- 缺点：Omniverse Python API 学习成本
- 适用：目标为发系统性论文，强调与工业标准集成

**建议方案**：
Phase 2 使用 Three.js；Phase 4 直接对接 Omniverse（跳过 UE5）。
理由：
1. Omniverse 是论文核心定位，越早接入越好
2. Omniverse Kit SDK 提供 Python API，比 UE5 C++ 插件更易集成
3. 接入 Omniverse 即可自动获得 USD 生态全栈渲染器（UE5、Blender、Maya 均可作为客户端）

### 音频渲染器
**短期**：Tone.js（浏览器端，够用）
**中期**：FMOD Studio（如需空间音频与复杂混响）

Poe 文本对音频渲染有特殊要求：
- Usher 的 *soundless day* → 极低环境音，近乎死寂
- Masque 舞会 → 音乐、人声、混响
- Pit and Pendulum 地牢 → 水流声、金属摩擦、极端混响

这些场景的音频差异比视觉差异更容易被人类感知，是跨模态一致性测试的优质素材。

---

## 三、对 LLEE-vs-Omniverse-Analysis.md 核心观点的回应
文章指出“LLEE 与 Omniverse 的对比存在偏差”，这一判断准确。
同时文章也给出了正确定位：
**LLEE 是 Omniverse 的 AI 前端，而非竞争者**

这一定位在文本选取层面有具体含义：

Poe 七间房的环境描写，经 LLEE 解析后会生成如下 Delta：
```json
{
  "visual": {
    "lights": [
      {"id": "room1", "color_temperature": 6500, "color_tint": [0.0, 0.0, 1.0]},
      {"id": "room2", "color_temperature": 5000, "color_tint": [0.5, 0.0, 0.5]},
      {"id": "room7", "color_temperature": 2000, "color_tint": [0.1, 0.0, 0.0]}
    ],
    "scene_type": "interior_palace_gothic"
  }
}
```

该 Delta 可直接驱动 Omniverse 的 USD Stage：每个房间为一个 USD Prim，光照参数通过 USD UsdLux schema 设置。
这就是“LLEE 作为 Omniverse AI 前端”的具体形态。

---

## 四、下一步等待的材料
1. **文本对确认**：starter-edition 与 light-origin 是否描述同一情节（Gate 0）
2. **更多文本**：如需更多极简版本可使用 Aladdin starter 片段；如需更多丰富版本，Poe 有大量可用素材
3. **实验材料**：ground truth 标注需人工完成，待文本确认后启动

**无需等待、可立即继续的工作**：
- Phase 0.5：编写 Parser Prompt 模板，启动 Prompt 稳定性测试
- 不依赖文本对，仅需 5 个任意段落即可

---

## 五、自由联想：Poe 作为 LLEE 的“压力测试”
Poe 文本的特殊性质：情绪多通过环境传递，而非角色内心独白。

> *a sense of insufferable gloom pervaded my spirit*
这是叙述者内心独白，属于 EXPLICIT。

但更多情绪通过环境暗示：
- *dull, dark, and soundless day* → 环境描写，非情绪陈述
- *bleak walls, vacant eye-like windows* → 拟人化描写，属于 CONTEXTUAL 级别情绪证据

这对 LLEE 构成一个关键挑战：
**环境描写是否应该触发情绪标注？**

严格 Zero-Introspection 原则的回答是：不应该。
*bleak walls* 是视觉描述，不是情绪证据。

但 Poe 的写作艺术恰恰在于用环境传递情绪，而非直接说“我很悲伤”。
如果 LLEE 完全忽略这种环境—情绪映射，就会丢失 Poe 文本的核心叙事机制。

这指向一个更深层问题：
**LLEE 的 Zero-Introspection 原则是否过于严格？**

或许需要新增一类证据：**ATMOSPHERIC**
- 环境描写暗示的氛围情绪
- 置信度上限 0.3
- 只影响叙事张力组（N.tension），不影响实体情绪（E.emotion）

如此一来：
*bleak walls* 不会让 Aladdor 变得悲伤，但会提升 N.tension，进而影响配乐张力参数。
这是一种更精细的区分：
**场景氛围（可从环境推断） vs 角色情绪（必须有直接证据）**