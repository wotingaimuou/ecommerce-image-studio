"""Compile an agent-authored brief; semantic analysis remains the host's job."""
import re
from pathlib import Path
from typing import Any

from .config import Config
from .utils import BriefError, keys, text_field

MODES = {"retouch", "hero", "carousel", "detail", "sku-color", "sku-bundle", "scene", "lifestyle", "ad"}
RATIOS = {"1:1", "3:4", "4:5", "16:9", "9:16", "4:3", "3:2", "2:3"}


def compile_brief(raw: Any, base: Path, cfg: Config) -> dict:
    """Return planned assets and exact built-in tool arguments, never fake images."""
    keys(raw, {"schema_version", "request", "product", "appearance_lock", "concept", "platform", "language", "style", "facts", "assumptions", "assets"}, "brief")
    if raw.get("schema_version") != 1 or type(raw.get("schema_version")) is not int:
        raise BriefError("schema_version 必须为 1")
    txt = lambda value, label, empty=False: text_field(value, label, cfg.max_text_chars, empty=empty)
    request = txt(raw.get("request"), "request")
    product = txt(raw.get("product"), "product")
    lock = txt(raw.get("appearance_lock"), "appearance_lock")
    concept = raw.get("concept", False)
    if type(concept) is not bool:
        raise BriefError("concept 必须为布尔值")
    platform = txt(raw.get("platform", "未指定平台"), "platform")
    language = txt(raw.get("language", "中文"), "language")
    style = txt(raw.get("style", "清晰可信的商品摄影"), "style")
    facts: dict[str, dict] = {}
    source_facts = raw.get("facts", [])
    if not isinstance(source_facts, list) or len(source_facts) > 256:
        raise BriefError("facts 必须为最多 256 项的列表")
    for fact in source_facts:
        keys(fact, {"id", "text", "source"}, "fact")
        fid = txt(fact.get("id"), "fact.id")
        if fid in facts:
            raise BriefError("fact.id 重复")
        facts[fid] = {"text": txt(fact.get("text"), "fact.text"), "source": txt(fact.get("source"), "fact.source")}
    assumptions = raw.get("assumptions", [])
    if not isinstance(assumptions, list) or len(assumptions) > 64:
        raise BriefError("assumptions 必须为最多 64 项的列表")
    assumptions = [txt(x, "assumption") for x in assumptions]
    assets = raw.get("assets")
    if not isinstance(assets, list) or not 1 <= len(assets) <= cfg.max_assets:
        raise BriefError(f"assets 数量须在 1 到 {cfg.max_assets}")
    output, seen = [], set()
    for asset in assets:
        keys(asset, {"id", "mode", "purpose", "composition", "scene", "ratio", "people", "copy", "fact_ids", "references", "transparent", "quantity", "color", "avoid"}, "asset")
        aid = txt(asset.get("id"), "asset.id")
        if not re.fullmatch(r"[a-z][a-z0-9-]{0,63}", aid) or aid in seen:
            raise BriefError("asset.id 须为唯一安全英文标识，首字符为小写字母")
        seen.add(aid)
        mode = asset.get("mode")
        if not isinstance(mode, str) or mode not in MODES:
            raise BriefError("未知 mode")
        ratio = asset.get("ratio", "3:4" if mode in {"detail", "lifestyle"} else "1:1")
        if not isinstance(ratio, str) or ratio not in RATIOS:
            raise BriefError("不支持的 ratio")
        people = asset.get("people", "none")
        if not isinstance(people, str) or people not in {"none", "faceless", "allowed"}:
            raise BriefError("people 应为 none/faceless/allowed")
        if mode == "hero" and people != "none":
            raise BriefError("保守 hero 模式不含人物；人物主图使用 carousel/ad")
        purpose = txt(asset.get("purpose"), "purpose")
        composition = txt(asset.get("composition"), "composition")
        scene = txt(asset.get("scene", ""), "scene", True)
        copy = asset.get("copy", [])
        if not isinstance(copy, list) or len(copy) > 32:
            raise BriefError("copy 必须为最多 32 项列表")
        copy = [txt(x, "copy") for x in copy]
        if mode in {"hero", "lifestyle"} and copy:
            raise BriefError("保守 hero / 随拍 lifestyle 不加文案；有文案主图用 carousel/ad")
        if mode in {"scene", "lifestyle"} and not scene:
            raise BriefError("场景模式须指定一个具体 scene")
        transparent = asset.get("transparent", False)
        if type(transparent) is not bool:
            raise BriefError("transparent 必须为布尔值")
        if transparent and mode in {"hero", "scene", "lifestyle"}:
            raise BriefError("透明与当前背景模式冲突；透明抠图使用 retouch")
        fact_ids = asset.get("fact_ids", [])
        if not isinstance(fact_ids, list) or any(not isinstance(x, str) or x not in facts for x in fact_ids):
            raise BriefError("fact_ids 引用了未知事实")
        references = asset.get("references", [])
        if not isinstance(references, list) or len(references) > cfg.max_references_per_asset:
            raise BriefError("参考图数量超过配置限制")
        refs, roles = [], []
        for ref in references:
            keys(ref, {"path", "role"}, "reference")
            role = ref.get("role")
            if role not in ("product", "template", "style"):
                raise BriefError("reference.role 无效")
            path = Path(txt(ref.get("path"), "reference.path")).expanduser()
            path = (base / path).resolve() if not path.is_absolute() else path.resolve()
            if not path.is_file():
                raise BriefError(f"参考图不存在: {path}")
            if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
                raise BriefError("参考图须为 PNG/JPEG/WebP")
            refs.append(str(path))
            roles.append(role)
        if not concept and "product" not in roles:
            raise BriefError("实物保真任务需要 product 参考；概念样图才可 concept=true")
        if mode in {"retouch", "sku-color", "sku-bundle"} and not refs:
            raise BriefError("编辑任务必须有参考图片")
        if mode in {"sku-color", "sku-bundle"} and "template" not in roles:
            raise BriefError("SKU 编辑必须有 template 母版")
        color = txt(asset.get("color", ""), "color", True)
        quantity = asset.get("quantity")
        if mode == "sku-color" and (not color or "product" not in roles):
            raise BriefError("换色需要 color 与本色 product 图")
        if mode == "sku-bundle":
            if type(quantity) is not int or not 1 <= quantity <= 100:
                raise BriefError("套装 quantity 须为 1 到 100 的整数")
            for line in copy:
                counts = re.findall(r"(\d+)\s*(?:件|个|只|pcs\b|packs?\b)", line, re.IGNORECASE)
                if any(int(number) != quantity for number in counts):
                    raise BriefError("套装文案件数与 quantity 冲突")
        elif quantity is not None:
            raise BriefError("quantity 仅适用于 sku-bundle")
        avoid = txt(asset.get("avoid", ""), "avoid", True)
        prompt = [
            "生成一张独立电商图片，不做拼图。" if mode not in {"detail", "carousel"} else "生成一张独立电商设计单页。",
            "概念样图，非实物保真证明。" if concept else "严格以 product 参考锁定商品外观，不能重新设计商品。",
            f"商品：{product}。外观锁定：{lock}",
            f"用途：{mode}；平台：{platform}；图内语言：{language}；目标画幅 {ratio}。",
            f"页面职责：{purpose}。构图：{composition}。视觉系统：{style}。",
        ]
        if refs:
            prompt.append("输入角色：" + "；".join(f"图{i+1}={role}" for i, role in enumerate(roles)) + "。product 决定商品；template 决定固定布局；style 仅参考视觉语言。")
        if scene:
            prompt.append(f"唯一核心场景：{scene}。不要混入其他空间。")
        if mode == "hero":
            prompt.append("纯白背景，产品完整清晰，真实接触阴影，无新增文案、角标、无关道具和人物。保留产品自身标签。")
        if mode == "lifestyle":
            prompt.append("自然环境光、普通手机随手拍质感、真实尺度与接触阴影，轻微生活痕迹。不是棚拍广告或 3D 渲染，不添加无关手机/相机道具。")
        if mode == "sku-color":
            prompt.append(f"只把母版商品替换为本色 product 图；目标色名 {color}。同步色名文字，其余布局、背景、字体层级、机位不变。")
        if mode == "sku-bundle":
            prompt.append(f"严格展示 {quantity} 件同款商品，尺寸一致且每件独立可数；已有数量相关文案同步为 {quantity} 件套，无数量文案时不新增。保持母版背景与信息布局。")
        prompt.append({"none": "不出现任何人物、人脸、手、脚或身体局部。", "faceless": "仅按构图使用人体局部，no visible face, face fully out of frame, no eyes, no nose, no mouth；镜面也不出现脸。", "allowed": "人物仅服务商品使用关系，产品为第一视觉中心。"}[people])
        prompt.append("图内文案仅限以下逐字内容：" + repr(copy) if copy else "不添加任何新文字、徽章、价格或促销标签；保留原有商品标签。")
        if fact_ids:
            prompt.append("已提供事实：" + "；".join(facts[x]["text"] for x in fact_ids))
        prompt.append("不编造参数、认证、功效、价格、销量、排名、服务承诺、配件、隐藏结构。未知信息省略，不在成品画待补充占位。无乱码、无水印。")
        if transparent:
            prompt.append("背景真实透明，保留商品边缘 alpha，不画棋盘格。")
        if avoid:
            prompt.append("用户禁止项：" + avoid)
        args: dict[str, Any] = {"prompt": "\n".join(prompt), "transparent_background": transparent}
        if refs:
            args["referenced_image_paths"] = refs
        output.append({"id": aid, "mode": mode, "ratio": ratio, "people": people, "quantity": quantity, "color": color, "copy": copy, "status": "planned", "output_file": aid + ".png", "tool_args": args})
    return {"schema_version": 1, "status": "planned", "request": request, "product": product, "concept": concept, "assumptions": assumptions, "facts": facts, "platform_rules_verified": False, "executor": "Codex host image_gen; CLI does not generate images", "assets": output}
