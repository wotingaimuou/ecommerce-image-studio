# 工程接口（用户无需填写）

自然语言由 Codex 解释；CLI 接收已经解释的 JSON，不使用正则猜商品。根节点只接受以下字段，未知字段报错，防止拼写错误被静默忽略。

- `schema_version`: 整数 1。
- `request`, `product`, `appearance_lock`: 非空字符串。
- `concept`: 布尔值，默认 false；仅明确概念样图可 true。
- `platform`, `language`, `style`: 字符串，可省略。
- `assumptions`: 假设字符串数组。
- `facts`: `{id, text, source}` 数组；source 写真实来源描述，脚本只核验引用存在，不判事实真假。
- `assets`: 每张图一个对象，1–64 项（配置可调，不是创意页数上限）。大量任务分批，保留全量订单，不能静默截断。

每个 asset：

| 字段 | 说明 |
|---|---|
| id | 唯一英文小写标识，首字符必须为小写字母，可含数字/连字符，最大 64 字符 |
| mode | retouch / hero / carousel / detail / sku-color / sku-bundle / scene / lifestyle / ad |
| purpose, composition | 必填；具体职责、景别、机位、产品与文字位置、光线 |
| scene | scene/lifestyle 必填；每图一个核心空间，组间一致性由 Agent 检查 |
| ratio | 1:1 / 3:4 / 4:5 / 16:9 / 9:16 / 4:3 / 3:2 / 2:3；是提示词目标，非保证输出尺寸 |
| people | none（默认）/ faceless / allowed |
| copy | 精确文案数组；hero/lifestyle 工作室模式不添加文案，有字主图请用 carousel/ad |
| fact_ids | facts 中已存在 id 的数组，正文卖点由 Agent 核验与这些事实一致 |
| references | `{path, role}` 数组；path 相对 brief 或绝对路径；role=product/template/style |
| transparent | 布尔值，默认 false；透明抠图用 retouch |
| color | sku-color 必填，配对应本色 product 参考和 template 母版 |
| quantity | sku-bundle 必填 1–100 整数；数量过多难以准确渲染，逐个检查 |
| avoid | 用户禁止项字符串 |

本地辅助器最多 5 张参考图/任务是工作室的保守配置，并非宣称工具统一上限。仅聊天附件的引用由宿主直接处理，不编造本地路径。

## 调用

```powershell
python scripts/studio.py plan --brief examples/concept-mug.json --out output/run-001
# Codex 读取 manifest，每项调用真实 image_gen；CLI 到此只有 planned。
python scripts/studio.py record --manifest output/run-001/manifest.json --asset mug-hero --image C:/absolute/generated.png --qa qa.json --out output/final-001
python scripts/studio.py error --kind unavailable --attempt 0
```

QA JSON：`reviewer`、`notes` 是非空字符串；`appearance`、`text`、`count`、`scene`、`people` 各为 `pass/fail/not_applicable/unverified`。
`record` 总是生成实际 PNG 和 receipt；比例/透明/视觉未通过时状态 `needs_review`、退出码 3；输入或 IO 错误退出 2；通过退出 0。不修改原 manifest，receipt 是完成凭证。不会静默覆盖。

错误处理：`unavailable/rate_limit` 明确失败可有限重试；`timeout/network/unknown` 先查已有结果；`permission/rejected/bad_input` 修正阻断再执行。错误分类是宿主决策辅助，不是替代真实 API 调用。
