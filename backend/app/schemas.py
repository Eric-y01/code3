"""各生成环节的 JSON Schema 定义。

统一接口保证：真实模型按此约束输出，Mock 引擎返回同构数据，前端渲染零差异。
同时提供“默认结构”，作为解析失败/字段缺失时的兜底，保证演示绝不因缺字段而崩。
"""
from __future__ import annotations

import json

# 各环节 key -> (schema 说明, mock 种子取值的字段名, 兜底默认结构工厂)
# schema 说明会被注入 prompt 引导模型按结构输出。
SCHEMA_SPECS = {
    "product_analysis": {
        "mock_key": "product_analysis",
        "description": (
            "对商品的分析结论，字段含义：\n"
            "product_name: 商品名称; category: 商品一级品类; "
            "appearance: 外观可见特征数组[{aspect 特征维度如颜色/造型/材质观感, detail 具体描述}]; "
            "style: 产品风格; scenes: 推断的适用场景数组; "
            "user_provided: 用户文本中提供的事实信息数组[{field 字段名, value 取值}]，只能来自用户文本，不得臆造; "
            "visual_uncertainty: 图片中看不清、需要用户补充确认的方面数组。"
        ),
    },
    "persona": {
        "mock_key": "persona",
        "description": (
            "目标用户画像，字段：name 画像代号; age_range; occupation 职业; "
            "spending_power 消费能力档位; purchase_scenes 购买场景数组; "
            "motivations 购买动机数组; pain_points 痛点数组; marketing_angle 一句话营销切入点。"
        ),
    },
    "titles": {
        "mock_key": "titles",
        "description": (
            "三平台标题：taobao/jd/xiaohongshu 三个子对象，每个含 {title, rationale}。"
            "规则：淘宝版 60 字内关键词堆叠风格; 京东版专业、参数化; 小红书版种草、口语化、可带 emoji。"
        ),
    },
    "selling_points": {
        "mock_key": "selling_points",
        "description": "五点卖点：{items: [{title 卖点短句, detail 卖点解释}]}，恰好 5 条，洞察消费者而非罗列参数。",
    },
    "detail_sections": {
        "mock_key": "detail_sections",
        "description": (
            "详情页结构五段：{sections: [{key, heading, content}]}，key 依次为 "
            "pain 消费者痛点 / solution 产品解决方案 / feature 核心功能 / scene 使用场景 / reason 购买理由，"
            "content 为可复制的段落文案。"
        ),
    },
    "video_script": {
        "mock_key": "video_script",
        "description": (
            "抖音/小红书短视频脚本：{title 视频标题, hook 前三秒钩子文案, format 内容形式说明, "
            "scenes: [{no 序号, time 时间轴, visual 画面分镜, voiceover 旁白台词, focus 产品展示点}], "
            "ending_call 结尾转化话术, hashtags 话题标签数组}。"
        ),
    },
    "image_plans": {
        "mock_key": "image_plans",
        "description": (
            "AI 营销图片方案（本版输出可直接投喂给 AI 绘图工具的提示词，不出图）。"
            "plans 为数组，每个方案含以下字段：\n"
            "name 场景方案名; ratio 画幅 如 1:1/3:4/16:9/4:3; usage 用于电商什么位置;\n"
            "subject 商品主体(外观/材质/颜色/结构细节，忠实于商品分析，不得虚构品牌或改动造型);\n"
            "scene 场景道具(背景材质颜色+道具+空间关系); lighting 光线影调(光源方向软硬/补光/阴影/氛围);\n"
            "composition 构图机位(焦段/机位高度/角度/景别/主体占比与位置); style 风格质感(摄影风格/材质真实度/画质);\n"
            "prompt 将上述五要素整合成的\"可直接粘贴\"完整正向提示词(中文，150字以上，要素齐全、含专业摄影与画质词);\n"
            "negative_prompt 负向提示词(文字水印/畸形/低质/穿帮等); tip 出图建议。"
            "给出 3-4 个互不重复的差异化场景方案。"
        ),
    },
}

# 解析失败时的兜底结构（保证渲染不崩，同时诚实标注空）
DEFAULTS = {
    "product_analysis": lambda: {
        "product_name": "", "category": "", "appearance": [],
        "style": "", "scenes": [], "user_provided": [], "visual_uncertainty": [],
    },
    "persona": lambda: {
        "name": "", "age_range": "", "occupation": "", "spending_power": "",
        "purchase_scenes": [], "motivations": [], "pain_points": [], "marketing_angle": "",
    },
    "titles": lambda: {
        "taobao": {"title": "", "rationale": ""},
        "jd": {"title": "", "rationale": ""},
        "xiaohongshu": {"title": "", "rationale": ""},
    },
    "selling_points": lambda: {"items": []},
    "detail_sections": lambda: {"sections": []},
    "video_script": lambda: {
        "title": "", "hook": "", "format": "", "scenes": [], "ending_call": "", "hashtags": [],
    },
    "image_plans": lambda: {"plans": []},
}

SCHEMA_KEYS = list(SCHEMA_SPECS.keys())

DETAIL_KEY_ORDER = ["pain", "solution", "feature", "scene", "reason"]
DETAIL_LABELS = {
    "pain": "消费者痛点", "solution": "产品解决方案", "feature": "核心功能",
    "scene": "使用场景", "reason": "购买理由",
}


def schema_text(key: str) -> str:
    return SCHEMA_SPECS[key]["description"]


def default_value(key: str) -> dict:
    return DEFAULTS[key]()


def merge_and_normalize(key: str, raw: object) -> dict:
    """把模型返回的任意 JSON 规整到符合默认结构（字段级防御）。"""
    base = default_value(key)
    if not isinstance(raw, dict):
        return base
    for k, v in raw.items():
        if k not in base:
            continue  # 丢弃未知字段
        base[k] = v
    # 逐类加固
    if key == "product_analysis":
        base["appearance"] = _arr(base["appearance"])
        base["scenes"] = _arr(base["scenes"])
        base["user_provided"] = _arr(base["user_provided"])
        base["visual_uncertainty"] = _arr(base["visual_uncertainty"])
        base["product_name"] = str(base["product_name"] or "")
        base["category"] = str(base["category"] or "")
        base["style"] = str(base["style"] or "")
    elif key == "persona":
        for f in ("purchase_scenes", "motivations", "pain_points"):
            base[f] = _arr(base[f])
        for f in ("name", "age_range", "occupation", "spending_power", "marketing_angle"):
            base[f] = str(base[f] or "")
    elif key == "titles":
        for p in ("taobao", "jd", "xiaohongshu"):
            o = base[p]
            if not isinstance(o, dict):
                o = {"title": "", "rationale": ""}
            base[p] = {"title": str(o.get("title", "") or ""), "rationale": str(o.get("rationale", "") or "")}
    elif key == "selling_points":
        items = []
        for it in _arr(base["items"]):
            if isinstance(it, dict) and (it.get("title") or it.get("detail")):
                items.append({"title": str(it.get("title", "")), "detail": str(it.get("detail", ""))})
        base["items"] = items[:5]
    elif key == "detail_sections":
        sections, seen = [], set()
        for s in _arr(base["sections"]):
            if not isinstance(s, dict) or not s.get("heading") and not s.get("content"):
                continue
            k = str(s.get("key", "") or "")
            sections.append({
                "key": k, "heading": str(s.get("heading", "") or ""),
                "content": str(s.get("content", "") or ""),
            })
            if k:
                seen.add(k)
        # 按标准顺序补全缺失段
        for k in DETAIL_KEY_ORDER:
            if k not in seen:
                sections.append({"key": k, "heading": DETAIL_LABELS[k], "content": ""})
        base["sections"] = sections
    elif key == "video_script":
        for f in ("title", "hook", "format", "ending_call"):
            base[f] = str(base[f] or "")
        scenes = []
        for s in _arr(base["scenes"]):
            if isinstance(s, dict):
                scenes.append({
                    "no": s.get("no", len(scenes) + 1),
                    "time": str(s.get("time", "") or ""),
                    "visual": str(s.get("visual", "") or ""),
                    "voiceover": str(s.get("voiceover", "") or ""),
                    "focus": str(s.get("focus", "") or ""),
                })
        base["scenes"] = scenes
        base["hashtags"] = _arr(base["hashtags"])
    elif key == "image_plans":
        plans = []
        for p in _arr(base["plans"]):
            if isinstance(p, dict) and (p.get("name") or p.get("prompt")):
                plans.append({
                    "name": str(p.get("name", "") or ""),
                    "ratio": str(p.get("ratio", "1:1") or "1:1"),
                    "usage": str(p.get("usage", "") or ""),
                    "subject": str(p.get("subject", "") or ""),
                    "scene": str(p.get("scene", "") or ""),
                    "lighting": str(p.get("lighting", "") or ""),
                    "composition": str(p.get("composition", "") or ""),
                    "style": str(p.get("style", "") or ""),
                    "prompt": str(p.get("prompt", "") or ""),
                    "negative_prompt": str(p.get("negative_prompt", "") or ""),
                    "tip": str(p.get("tip", "") or ""),
                })
        base["plans"] = plans
    return base


def _arr(v: object) -> list:
    if isinstance(v, list):
        return v
    if isinstance(v, str) and v:
        return [v]
    if isinstance(v, dict):
        return [v]
    return []


def schema_json_text(key: str) -> str:
    """给模型看的 JSON 结构示意（示例形态）。"""
    sample = {
        "product_analysis": {
            "product_name": "智能保温杯", "category": "水具",
            "appearance": [{"aspect": "颜色", "detail": "磨砂黑"}],
            "style": "商务简约", "scenes": ["办公", "通勤"],
            "user_provided": [{"field": "材质", "value": "304不锈钢"}],
            "visual_uncertainty": ["容积大小"],
        },
        "persona": {
            "name": "都市通勤白领", "age_range": "25-35", "occupation": "白领",
            "spending_power": "中高", "purchase_scenes": ["办公室补水"], "motivations": ["健康"],
            "pain_points": ["久坐缺水"], "marketing_angle": "把喝水变成低负担的日常习惯",
        },
        "titles": {
            "taobao": {"title": "示例", "rationale": "原因"},
            "jd": {"title": "示例", "rationale": "原因"},
            "xiaohongshu": {"title": "示例", "rationale": "原因"},
        },
        "selling_points": {"items": [{"title": "卖点短句", "detail": "卖点解释"}]},
        "detail_sections": {"sections": [{"key": "pain", "heading": "消费者痛点", "content": "正文"}]},
        "video_script": {
            "title": "示例标题", "hook": "前3秒钩子", "format": "口播+实拍",
            "scenes": [{"no": 1, "time": "0-2s", "visual": "画面", "voiceover": "旁白", "focus": "展示点"}],
            "ending_call": "结尾转化", "hashtags": ["好物推荐"],
        },
        "image_plans": {
            "plans": [{
                "name": "白底电商主图", "ratio": "1:1", "usage": "淘宝主图",
                "subject": "磨砂黑直筒保温杯：304不锈钢哑光磨砂金属机身，顶部圆形LED温度屏，杯盖与杯身同色，无手柄",
                "scene": "纯白无缝背景棚拍，浅灰台面映出柔和倒影，画面大面留白，无额外道具",
                "lighting": "顶部大柔光箱为主光、左右加反光板补光，均匀漫射，杯身呈现细腻金属磨砂层次，投影轻淡干净",
                "composition": "85mm 定焦，机位与杯身中部齐平，居中对称构图，杯身约占画面55%，带轻微 3° 俯视",
                "style": "商业产品摄影，真实材质还原，清晰锐利，超高细节，8K 质感",
                "prompt": "（把上述五要素整合成一段可直接粘贴的完整中文正向提示词，150字以上，要素齐全、含专业摄影与画质关键词）",
                "negative_prompt": "文字水印, 低质量, 畸形杯身, 过度HDR, 阴影脏乱, 多余人物",
                "tip": "出图建议",
            }]
        },
    }
    return json.dumps(sample.get(key, {}), ensure_ascii=False, indent=1)
