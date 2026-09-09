"""报告 → Markdown（可导出，亦可被前端下载为 .md / 打印为 PDF）。"""
from __future__ import annotations

from typing import Any


def _source_badge(source: str) -> str:
    return "（视觉推断）" if source == "visual" else "（用户提供）"


def render_markdown(report: dict[str, Any]) -> str:
    m = report.get("meta", {})
    lines: list[str] = []

    lines.append("# AI 电商商品运营报告\n")
    lines.append(f"- 生成时间：{m.get('generated_at', '')}")
    lines.append(f"- 模式：{'Mock 演示' if m.get('is_mock') else '真实模型'}"
                 f"（供应商 {m.get('provider', '')}，视觉 {m.get('model_vision', '')} / 文本 {m.get('model_text', '')}）")
    lines.append(f"- 是否命中缓存：{'是' if m.get('from_cache') else '否'}")
    lines.append(f"- 商品图：{m.get('image_url', '')}")
    if m.get("cutout_url"):
        lines.append(f"- 主体抠图：{m.get('cutout_url', '')}")
    ui = m.get("user_input", {}) or {}
    if ui.get("product_name") or ui.get("description"):
        lines.append(f"- 用户补充：名称「{ui.get('product_name') or '无'}」· 说明「{ui.get('description') or '无'}」")
    lines.append("")

    # 1 商品分析
    p = report.get("product", {}) or {}
    lines.append("## 一、商品智能分析\n")
    lines.append(f"- **名称**：{p.get('product_name') or '—'}")
    lines.append(f"- **品类**：{p.get('category') or '—'}")
    lines.append(f"- **风格**：{p.get('style') or '—'}")
    if p.get("appearance"):
        lines.append("\n**外观特征：**")
        for a in p["appearance"]:
            if isinstance(a, dict) and a.get("aspect"):
                lines.append(f"- {a['aspect']}：{a.get('detail', '')}")
    if p.get("scenes"):
        lines.append(f"\n**推断场景：**{('、'.join(map(str, p['scenes'])))}")
    if p.get("user_provided"):
        lines.append("\n**用户提供的事实信息：**")
        for u in p["user_provided"]:
            if isinstance(u, dict) and u.get("field"):
                lines.append(f"- {u['field']}：{u.get('value', '')}")
    if p.get("visual_uncertainty"):
        lines.append(f"\n**需用户进一步确认（模型视觉边界）**：{('、'.join(map(str, p['visual_uncertainty'])))}")
    lines.append("")

    # 2 用户画像
    per = report.get("persona", {}) or {}
    lines.append("## 二、目标用户画像\n")
    if per.get("name"):
        lines.append(f"- 画像代号：{per['name']}")
    if per.get("age_range"):
        lines.append(f"- 年龄：{per['age_range']}")
    for k, label in (("occupation", "职业"), ("spending_power", "消费能力")):
        if per.get(k):
            lines.append(f"- {label}：{per[k]}")
    for k, label in (("purchase_scenes", "购买场景"), ("motivations", "购买动机"), ("pain_points", "痛点")):
        v = per.get(k) or []
        if v:
            lines.append(f"- {label}：{('、'.join(map(str, v)))}")
    if per.get("marketing_angle"):
        lines.append(f"- **营销切入点**：{per['marketing_angle']}")
    lines.append("")

    # 3 三平台标题
    t = report.get("titles", {}) or {}
    lines.append("## 三、电商标题（按平台分版）\n")
    for key, label in (("taobao", "淘宝版"), ("jd", "京东版"), ("xiaohongshu", "小红书版")):
        item = t.get(key) or {}
        if item.get("title"):
            lines.append(f"### {label}\n")
            lines.append(f"{item['title']}\n")
            if item.get("rationale"):
                lines.append(f"> 创作思路：{item['rationale']}\n")
    lines.append("")

    # 4 五点卖点
    sp = report.get("selling_points", {}) or {}
    lines.append("## 四、五点卖点\n")
    for i, item in enumerate((sp.get("items") or []), 1):
        if isinstance(item, dict) and item.get("title"):
            lines.append(f"{i}. **{item['title']}**：{item.get('detail', '')}")
    lines.append("")

    # 5 详情页
    ds = report.get("detail_sections", {}) or {}
    lines.append("## 五、商品详情页文案\n")
    for s in ds.get("sections") or []:
        if isinstance(s, dict) and (s.get("heading") or s.get("content")):
            lines.append(f"### {s.get('heading') or ''}\n")
            lines.append(f"{s.get('content', '')}\n")
    lines.append("")

    # 6 短视频脚本
    vs = report.get("video_script", {}) or {}
    lines.append("## 六、短视频脚本（抖音/小红书）\n")
    if vs.get("title"):
        lines.append(f"- 视频标题：{vs['title']}")
    if vs.get("format"):
        lines.append(f"- 内容形式：{vs['format']}")
    if vs.get("hook"):
        lines.append(f"- **前三秒钩子**：{vs['hook']}\n")
    if vs.get("scenes"):
        lines.append("| 镜头 | 时间 | 画面 | 产品展示 | 旁白 |")
        lines.append("| --- | --- | --- | --- | --- |")
        for sc in vs["scenes"]:
            if isinstance(sc, dict):
                lines.append(f"| {sc.get('no', '')} | {sc.get('time', '')} | {sc.get('visual', '')} | "
                             f"{sc.get('focus', '')} | {sc.get('voiceover', '')} |")
        lines.append("")
    if vs.get("ending_call"):
        lines.append(f"**结尾转化**：{vs['ending_call']}")
    if vs.get("hashtags"):
        lines.append(f"\n**话题标签**：{(' '.join('#' + str(h) for h in vs['hashtags']))}")
    lines.append("")

    # 7 营销图方案
    ip = report.get("image_plans", {}) or {}
    lines.append("## 七、AI 营销图片方案（Prompt 版）\n")
    for plan in ip.get("plans") or []:
        if not isinstance(plan, dict) or not plan.get("name"):
            continue
        lines.append(f"### {plan['name']}（{plan.get('ratio', '')} · {plan.get('usage', '')}）\n")
        for k, label in (("subject", "商品主体"), ("scene", "场景道具"), ("lighting", "光线影调"),
                         ("composition", "构图机位"), ("style", "风格质感")):
            v = plan.get(k)
            if isinstance(v, str) and v:
                lines.append(f"- **{label}**：{v}")
        lines.append(f"\n**完整正向 Prompt**：\n\n```\n{plan.get('prompt', '')}\n```\n")
        if plan.get("negative_prompt"):
            lines.append(f"**负向 Prompt**：{plan['negative_prompt']}")
        if plan.get("tip"):
            lines.append(f"**出图建议**：{plan['tip']}")
        lines.append("")
    lines.append("---\n")
    lines.append("*由 AI 电商运营助手生成，内容供运营参考，发布前请人工核验商品事实信息。*")
    return "\n".join(lines)
