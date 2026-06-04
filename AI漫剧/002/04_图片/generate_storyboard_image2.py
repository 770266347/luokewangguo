import subprocess
from pathlib import Path


CLIENT = Path(r"E:\luokewangguo\image2接口\gpt_image2_client.py")
OUT_DIR = Path(r"E:\luokewangguo\AI漫剧\002\04_图片")
REF_DIR = OUT_DIR / "references"
SCENE_REF = OUT_DIR / "闪耀大赛赛场参考图.jpg"


COMMON = "\n".join(
    [
        "生成 16:9 横屏分镜关键帧。风格必须是针毡毛绒定格动画风格，像手工毛毡小精灵和微缩赛场布景。背景是闪耀大赛赛场，即洛克王国 PVP 比赛场景：夜晚学院城堡庭院，中央圆形对战擂台，金色圆环地面，蓝灰色石板广场，对称拱廊和台阶，石柱路灯，红色城堡建筑，蓝色尖顶屋顶，蓝色旗帜，比赛灯光。",
        "只参考输入图里的角色造型和场景构图，不要复刻 UI、角色列表、任务文字、小地图、按钮、血条、玩家角色、原图文字、水印、logo。",
        "所有角色保持可爱、荒诞、安全，不血腥，不受伤，不痛苦。",
    ]
)


TASKS = [
    {
        "output": "scene_001_a_key.png",
        "images": [SCENE_REF],
        "prompt": "\n".join(
            [
                COMMON,
                "镜头 scene_001_a：闪耀大赛赛场开场空镜。画面没有任何精灵。中央圆形对战擂台干净开阔，前景是蓝灰色石板广场，远处红色城堡和蓝色旗帜清楚。镜头正面略俯视，保留足够空间给后续三队登场。",
                "不要任何文字、字幕、UI、按钮、小地图、人物、精灵。",
            ]
        ),
    },
    {
        "output": "scene_001_b_key_v2.png",
        "images": [
            SCENE_REF,
            REF_DIR / "144_雪影娃娃.png",
            REF_DIR / "136_雪巨人.png",
            REF_DIR / "322_月牙雪熊.png",
        ],
        "prompt": "\n".join(
            [
                COMMON,
                "镜头 scene_001_b：雪天队正面登场首帧。雪影娃娃、雪巨人、月牙雪熊三只精灵正面站在圆形擂台前方，雪影娃娃在中间靠前，雪巨人和月牙雪熊分站两侧，形成正面三角构图。冰蓝雪花刚从它们脚下铺向圆形擂台，三只精灵必须都清楚可辨认，毛绒材质统一。",
                "不要新增角色，不要文字字幕，不要 UI，不要把雪巨人画成人类，不要漏掉任何一只雪天队精灵，不要画成动作完成后的结果图。",
            ]
        ),
    },
    {
        "output": "scene_001_c_key_v2.png",
        "images": [
            SCENE_REF,
            REF_DIR / "029_布克棱岩.png",
            REF_DIR / "192_棋契陛下.png",
            REF_DIR / "155_针叶巡林.png",
        ],
        "prompt": "\n".join(
            [
                COMMON,
                "镜头 scene_001_c：沙暴队正面登场首帧。布克棱岩、棋契陛下、针叶巡林三只精灵正面站在圆形擂台前方，布克棱岩在中间靠前，棋契陛下和针叶巡林分站两侧，形成正面三角构图。沙尘、毛绒地刺、棋盘战术线刚从脚边开始展开，三只精灵必须都清楚可辨认。",
                "不要新增角色，不要文字字幕，不要 UI，不要真实棋盘贴图，不要漏掉针叶巡林，不要把布克棱岩画成虫形或紫色兽，不要画成动作完成后的结果图。",
            ]
        ),
    },
    {
        "output": "scene_001_d_key.png",
        "images": [
            SCENE_REF,
            REF_DIR / "084_女王蜂.png",
            REF_DIR / "101_花衣蝶.png",
            REF_DIR / "284_铠甲虫.png",
        ],
        "prompt": "\n".join(
            [
                COMMON,
                "镜头 scene_001_d：虫队登场。女王蜂、花衣蝶、铠甲虫三只精灵在闪耀大赛赛场另一侧同框，三只一起喊话。虫群形成环形包围网，花衣蝶轻微飞动，铠甲虫守住阵型。三只精灵必须都清楚可辨认。",
                "不要新增角色，不要文字字幕，不要 UI，不要恐怖虫群，不要密集恶心画面，不要漏掉花衣蝶或铠甲虫。",
            ]
        ),
    },
    {
        "output": "scene_002_a_key.png",
        "images": [
            SCENE_REF,
            OUT_DIR / "scene_001_b_key_v2.png",
            OUT_DIR / "scene_001_c_key_v2.png",
            OUT_DIR / "scene_001_d_key.png",
        ],
        "prompt": "\n".join(
            [
                COMMON,
                "镜头 scene_002_a：三队混战与预警。雪天队、沙暴队、虫队九只精灵在闪耀大赛赛场中央卡通式互殴。雪花、地刺、沙尘、虫群乱飞，但所有角色都安全、不受伤。低沉战鼓声靠近后混战突然停住，三队代表看向赛场入口方向。画面要乱中有序，九只精灵不能挤成一团。",
                "不要巨鼓象完整出现，只能暗示入口方向有动静。不要文字字幕，不要 UI，不要血腥，不要痛苦表情。",
            ]
        ),
    },
    {
        "output": "scene_002_b_key_v2.png",
        "images": [SCENE_REF, REF_DIR / "372_巨鼓象.png"],
        "prompt": "\n".join(
            [
                COMMON,
                "镜头 scene_002_b：巨鼓象倒立鼓轮登场。巨鼓象以夸张倒立鼓轮形态从闪耀大赛赛场入口滚入，低机位侧向构图。必须保留巨鼓象本体、象鼻、鼓形机械结构、四条象腿和精灵特征；鼓面竖直立起，头和象鼻朝下，两条长腿向下撑开，头和象鼻倒挂在鼓面下方，两侧金色螺旋部件展开，以游戏内滚动姿态快速滚动；表情慌而不凶，像想停但停不下来。可以有轻微说话表情。",
                "不要汽车化，不要变成普通轮胎、贴地车轮或车辆，不要把鼓面画成轮胎贴地转动，不要人形化，不要新增角色，不要人类观众或玩家角色，不要少腿或把腿藏没，不要文字字幕，不要 UI。",
            ]
        ),
    },
]


def run_task(task: dict) -> None:
    output = OUT_DIR / task["output"]
    cmd = [
        "py",
        "-3",
        str(CLIENT),
        "edit",
        "--size",
        "1536x864",
        "--quality",
        "medium",
        "--output-format",
        "png",
        "-o",
        str(output),
        "-p",
        task["prompt"],
    ]
    for image in task["images"]:
        if not Path(image).exists():
            raise FileNotFoundError(f"Missing reference image: {image}")
        cmd.extend(["--image", str(image)])

    print(f"Generating {task['output']} ...", flush=True)
    subprocess.run(cmd, check=True)


def main() -> None:
    for task in TASKS:
        run_task(task)


if __name__ == "__main__":
    main()


