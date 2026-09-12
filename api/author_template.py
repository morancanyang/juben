"""Separate teaching case; contains no secrets from the three official cases."""

from api.seed_content import character, evidence, question, scene, statement


def make_template():
    actors = [
        character(
            "an",
            "安宁",
            "夜班管理员",
            "负责展厅钥匙与日常盘点。",
            "简洁，有问必答。",
            "#a5b49b",
            [
                statement(
                    "an_1",
                    "十九点十分我在前台交班，展厅里只有陈默在调试灯光。",
                    ["时间", "经过", "哪里"],
                ),
                statement(
                    "an_2",
                    "展柜的机械钥匙整晚都在我手里；备用电子授权需要维护卡。",
                    ["钥匙", "展柜", "授权"],
                ),
            ],
        ),
        character(
            "chen",
            "陈默",
            "灯光师",
            "负责临时灯光安装，佩戴一张维护卡。",
            "谨慎，倾向陈述工作流程。",
            "#bba890",
            [
                statement(
                    "chen_1",
                    "我在十九点以后独自调灯。展柜开关不属于我的工作范围。",
                    ["时间", "灯", "经过"],
                ),
                statement(
                    "chen_2", "C-04 是我的维护卡，没有借给过别人。", ["卡", "编号"]
                ),
            ],
        ),
    ]
    case = {
        "schema_version": "1.0",
        "id": "museum-example",
        "title": "展柜里的空位",
        "subtitle": "一枚银徽章，在闭馆前消失。",
        "description": "小型展览馆的银徽章不见了。展柜没有被破坏，两名工作人员各执一词。你需要根据日志与现场物证找出取走它的人。",
        "intro": "19:30，展馆闭馆。安宁盘点时发现银徽章消失，馆门仍然关闭。你作为受邀侦探，开始核查展柜、前台与工作人员物品。此为创作教学案件，无死亡情节。",
        "genre": "本格推理",
        "difficulty": "入门",
        "duration": 15,
        "cover": "manor",
        "tags": ["教学案件", "物证比对"],
        "warnings": [],
        "characters": actors,
        "scenes": [
            scene(
                "gallery",
                "小展厅",
                "第一现场",
                "展柜完整，电子开关的指示灯仍亮着。前台就在几步之外。",
                [
                    ("展柜日志", "电子控制器保留最近一次开柜时间。", "log"),
                    ("工作手套", "陈默交出当天的工作手套。", "glove"),
                    ("收购便笺", "工作人员休息桌上有一张便笺。", "note"),
                ],
            )
        ],
        "evidence": [
            evidence(
                "log",
                "开柜日志",
                "record",
                "19:12，维护卡 C-04 打开展柜。",
                "卡片为陈默实名签收。日志完整，排除了机械钥匙开柜。",
                "展厅 · 控制器",
                "19:12",
                ["chen"],
            ),
            evidence(
                "glove",
                "银粉手套",
                "trace",
                "手套掌心留有银色粉末。",
                "粉末与银徽章表面保护层吻合；徽章边缘的新划痕与手套硬胶点间距一致。",
                "陈默 · 工作手套",
                "19:12",
                ["chen"],
            ),
            evidence(
                "note",
                "收藏商收购便笺",
                "document",
                "便笺约定当晚收购一枚相同编号的银徽章。",
                "陈默签了姓名，并留下自己的收款账号。便笺提供了转卖获利动机。",
                "展厅 · 休息桌",
                "当日",
                ["chen"],
            ),
        ],
        "combinations": [],
        "triggers": [],
        "questions": [
            question(
                "culprit", "谁取走了徽章？", [(a["id"], a["name"]) for a in actors]
            ),
            question(
                "motive",
                "动机是什么？",
                [("sale", "转卖获利"), ("protect", "转移保管")],
            ),
            question(
                "method",
                "如何打开展柜？",
                [("card", "使用维护卡打开"), ("key", "使用机械钥匙打开")],
            ),
            question("time", "什么时候打开？", [("1912", "19:12"), ("1930", "19:30")]),
            question(
                "location",
                "关键行动在哪里？",
                [("gallery", "小展厅"), ("desk", "前台")],
            ),
            question(
                "tool",
                "使用了什么工具？",
                [("card", "C-04 维护卡"), ("key", "机械钥匙")],
            ),
            question(
                "accomplice", "是否存在共犯？", [("none", "无共犯"), ("an", "安宁")]
            ),
        ],
        "answer": {
            "culprit": "chen",
            "motive": "sale",
            "method": "card",
            "time": "1912",
            "location": "gallery",
            "tool": "card",
            "accomplice": "none",
        },
        "key_evidence": ["log", "glove", "note"],
        "truth": [
            {
                "title": "取走徽章的人",
                "text": "陈默独自取走徽章，准备按便笺中的约定转卖获利。",
            },
            {
                "title": "可核验的行动",
                "text": "19:12，C-04 维护卡打开展柜。日志与陈默关于无人借卡的陈述相互印证，手套残留形成独立物证。",
            },
            {
                "title": "误导与证据",
                "text": "安宁持有机械钥匙看似可疑，但本次开柜实际使用电子卡。持有某种权限本身不等于本次实施行为。",
            },
        ],
    }
    return case
