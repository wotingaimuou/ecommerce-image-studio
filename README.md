<div align="center">

# 电商生图工作室
### 一张商品图，一句话，一套有分工的电商视觉。

**Ecommerce Image Studio · Codex Skill**

主图 · 详情页 · SKU · 套装 · 商业场景 · 手机随拍

[快速开始](#快速开始) · [看完整案例](showcase/mora/README.md) · [使用指南](docs/USAGE.md) · [技术原理](docs/ARCHITECTURE.md)

</div>

![MORA 暮色主视觉——AI 虚构商品演示](showcase/mora/images/campaign.png)

> **展示说明：** MORA 是为本仓库创作的虚构香水概念，品牌、包装与 50 mL 容量均为演示设定。图片由内置图像工具实际生成，不代表真实品牌合作、真实商品拍摄或经营效果。

## 从一张母图，到一套视觉

<table>
<tr>
<td width="33%"><img src="showcase/mora/images/product-master.png" alt="虚构商品母图"></td>
<td width="33%"><img src="showcase/mora/images/details.png" alt="设计细节页"></td>
<td width="33%"><img src="showcase/mora/images/lifestyle.png" alt="AI窗边场景"></td>
</tr>
<tr>
<td align="center"><b>商品母图</b><br>先建立瓶形、配色和标签</td>
<td align="center"><b>设计细节</b><br>用图文解释形体与质感</td>
<td align="center"><b>生活场景</b><br>让同一商品进入日常空间</td>
</tr>
</table>

这个案例的重点是：每一张图承担不同的信息任务，共用同一商品外观约束。完整的原始需求、brief、实际提示词和质检记录都在 [MORA 案例](showcase/mora/README.md) 中。

## 它有什么特点

| 特点 | 具体做什么 |
| --- | --- |
| 一句话启动 | 读取商品图，主动整理用途、款式、场景、文案和限制，用户不用填写 JSON。 |
| 先理解，再出图 | 为每张图片指定职责：识别商品、看清细节、理解规格或选择款式。 |
| 三种参考角色 | `product` 锁商品，`template` 锁版式，`style` 提供视觉语言，避免把风格参考当商品事实。 |
| 同一商品，多种场景 | 主图、轮播、详情页、多色 SKU、数量套装、商业场景和自然随拍使用不同构图。 |
| 参数有来源 | 价格、材质、尺寸和卖点来自用户资料；看见金属光泽不等于知道材质。 |
| 真正调用生图 | Skill 指导宿主逐张调用图像工具，辅助脚本生成的计划不冒充图片成品。 |
| 逐张质检 | 检查文字、外观、SKU、件数、人物、比例和透明度，失败只修对应图片。 |
| 有交付记录 | 保留 brief、提示词和验收结果，区分 `planned`、`accepted` 与 `needs_review`。 |

**能力边界：** 这是给具备图像生成能力的 Codex 宿主使用的 Skill。仓库里的 Python CLI 负责编译计划和记录验收，单独运行不会调用图像模型，也不会自动发布到电商平台。生成式编辑不能保证逐像素保真，小刻字、Logo、精密结构及材质承诺应核对实物。

## 快速开始

### 1. 安装 Skill

需要 Git，以及能加载本地 Skill、调用图像工具的 Codex 环境。实际图像工具是否可用取决于你的宿主和账号。默认工作流无需向本项目填写 API key。

**Windows / PowerShell：**

```powershell
$skillBase = if ($env:CODEX_HOME) { Join-Path $env:CODEX_HOME 'skills' } else { Join-Path $env:USERPROFILE '.codex/skills' }
$skillTarget = Join-Path $skillBase 'ecommerce-image-studio'
if (Test-Path -LiteralPath $skillTarget) { throw '该技能目录已存在，请先备份或选择其他位置。' }
New-Item -ItemType Directory -Path $skillBase -Force | Out-Null
git clone https://github.com/wotingaimuou/ecommerce-image-studio.git $skillTarget
```

**macOS / Linux：**

```bash
skill_base="${CODEX_HOME:-$HOME/.codex}/skills"
mkdir -p "$skill_base"
git clone https://github.com/wotingaimuou/ecommerce-image-studio.git "$skill_base/ecommerce-image-studio"
```

重新加载技能或开启新对话，确认技能列表中出现“电商生图工作室”。如你的宿主使用其他 Skill 目录，将仓库完整放入对应目录即可。

### 2. 上传商品图，直接说需求

```text
$ecommerce-image-studio
这款项链准备在拼多多上卖。
请根据商品图制作主图、佩戴氛围、尺寸说明和选款图，
先整理每张图的作用，再实际出图并逐张质检。
材质、尺寸和售价使用我提供的信息，未知内容不要编造。
```

不必一次想清所有设计参数。非关键项会采用合理默认值；商品身份、套装数量、实物参考等关键内容不清楚时，会先询问。

### 3. 收到什么

每张独立图片，以及统一 brief、实际提示词、质检记录。套图的张数依据信息量规划，不固定凑成 6 张或 8 张。

## 还可以这样用

| 需求 | 直接发给 Codex 的话 |
| --- | --- |
| 干净主图 | “保留商品结构和标签，做一张浅色背景主图，不加文案。” |
| 详情页 | “先梳理买家的疑问，再做一套解释外观、尺寸、用法的详情页。” |
| 多色 SKU | “这三张分别是三种颜色。用同一版式展示，色名按我的标注。” |
| 数量套装 | “参考母版做 3 件套，三件都要完整可数，不添加赠品。” |
| 日常氛围 | “在窗边木桌上自然随拍，保持真实商品外观，不加海报文字。” |
| 跨境素材 | “面向英语市场，文案简短，使用我提供的英文商品名和规格。” |

## 可选：运行编排与验收 CLI

日常对话不要求用户操作 CLI。开发者或需要复现过程的用户可以使用 Python 3.10+：

```bash
python -m venv .venv
# 激活虚拟环境后：
python -m pip install -r requirements.txt
python scripts/studio.py plan --brief examples/concept-mug.json --out .local-run/mug
```

输出 `manifest.json` 和逐张提示词；状态为 `planned`，**这一步没有生成图片**。随后由支持图像工具的宿主执行 `tool_args`，检查结果，再运行 `record`。

完整示例见 [使用指南](docs/USAGE.md)，参数见 [数据接口](references/schema.md)。

## 仓库结构

```text
SKILL.md                  Codex 入口与执行规则
agents/openai.yaml        技能展示信息
references/               场景路由、字段说明、质检清单
scripts/studio.py         编排 / 验收 CLI
src/                      校验、提示词编译、图像检查
examples/                 最小可运行 brief 和 QA 示例
showcase/mora/            虚构品牌完整案例与真实生成结果
docs/                     使用方法和实现原理
tests/                    关键约束与验收行为测试
```

## 当前验证范围

本地验证覆盖 brief 编译、参考图完整性、数量约束、无参考时的实物任务拒绝、比例和透明度检查、未验证图片不判为通过、输出防覆盖。仓库中的案例是一次实际生成结果，不保证每次重跑得到相同像素、相同耗时或相同文字质量。

平台最新上传规格需在商家后台核实。场景素材请按 AI 生成素材使用；不要冒充买家评价、真实订单或认证证明。

