import math

from flask import Flask, render_template, request

app = Flask(__name__)

NAME_MAX_LENGTH = 50

# 體位分類（臺灣成人標準）。"upper" 為該區間的上限（不含），最後一個區間沒有上限。
BMI_CATEGORIES = (
    {
        "key": "underweight",
        "label": "體重過輕",
        "short_label": "過輕",
        "tone": "low",
        "upper": 18.5,
        "risk_level": "中等",
        "risk_level_key": "moderate",
        "advice": "留意是否攝取足夠且均衡的營養，規律進食並搭配適度肌力活動；若體重持續下降，建議諮詢醫師或營養師。",
        "risks": (
            "營養攝取不足可能造成免疫力下降、容易疲倦或貧血。",
            "骨質密度偏低，長期可能提高骨質疏鬆與骨折的風險。",
            "若伴隨食慾不振、月經不規則或體重持續下降，建議及早就醫評估。",
        ),
    },
    {
        "key": "healthy",
        "label": "健康體位",
        "short_label": "正常",
        "tone": "healthy",
        "upper": 24,
        "risk_level": "較低",
        "risk_level_key": "low",
        "advice": "維持均衡飲食與規律運動，並持續留意睡眠及生活習慣，幫助保持健康體位。",
        "risks": (
            "目前體位落在健康範圍，體重相關慢性病的風險相對較低。",
            "BMI 無法反映體脂肪與肌肉量，仍建議留意腰圍（男性未滿 90 公分、女性未滿 80 公分）。",
            "維持規律運動與均衡飲食，並定期健康檢查追蹤血壓、血糖與血脂。",
        ),
    },
    {
        "key": "overweight",
        "label": "體重過重",
        "short_label": "過重",
        "tone": "high",
        "upper": 27,
        "risk_level": "中等",
        "risk_level_key": "moderate",
        "advice": "可從減少含糖飲料、增加蔬菜與日常活動量開始，循序建立適合自己的健康習慣。",
        "risks": (
            "高血壓、血脂異常與第 2 型糖尿病等代謝疾病的風險開始上升。",
            "若腰圍超過標準（男性 90 公分、女性 80 公分以上），代謝症候群的風險更高。",
            "建議每週累積至少 150 分鐘中等強度運動，並逐步調整飲食內容。",
        ),
    },
    {
        "key": "obese",
        "label": "肥胖",
        "short_label": "肥胖",
        "tone": "obese",
        "upper": None,
        "risk_level": "較高",
        "risk_level_key": "high",
        "advice": "建議與醫師或營養師討論適合自己的飲食及運動計畫，並留意血壓、血糖等健康指標。",
        "risks": (
            "第 2 型糖尿病、心血管疾病、脂肪肝與睡眠呼吸中止症的風險明顯提高。",
            "體重會加重膝關節與腰椎負擔，也與部分癌症風險上升有關。",
            "建議諮詢醫師或營養師，訂定可持續的體重管理計畫並定期追蹤健康指標。",
        ),
    },
)

# 儀表板刻度範圍與 SVG 幾何（viewBox 使用者座標）。
GAUGE_MIN = 15
GAUGE_MAX = 35
GAUGE_VIEW_BOX = "0 0 400 250"
GAUGE_CENTER_X = 200.0
GAUGE_CENTER_Y = 190.0
GAUGE_RADIUS = 140.0
GAUGE_LABEL_RADIUS = 174.0
GAUGE_NEEDLE_LENGTH = 120.0
GAUGE_TICK_OUTER_RADIUS = 123.0
GAUGE_MINOR_TICK_INNER_RADIUS = 115.0
GAUGE_MAJOR_TICK_INNER_RADIUS = 106.0
GAUGE_SEGMENT_GAP_DEGREES = 0.7
GAUGE_VALUE_Y = 240.0


def bmi_guidance(bmi):
    for category in BMI_CATEGORIES[:-1]:
        if bmi < category["upper"]:
            return dict(category)
    return dict(BMI_CATEGORIES[-1])


def _gauge_fraction(bmi):
    fraction = (bmi - GAUGE_MIN) / (GAUGE_MAX - GAUGE_MIN)
    return min(max(fraction, 0.0), 1.0)


def _gauge_point(fraction, radius):
    # 半圓儀表板：fraction 0 為左端點，1 為右端點，沿上方弧線順時針前進。
    angle = math.pi * fraction
    return GAUGE_CENTER_X - radius * math.cos(angle), GAUGE_CENTER_Y - radius * math.sin(angle)


def _arc_path(start_fraction, end_fraction):
    x1, y1 = _gauge_point(start_fraction, GAUGE_RADIUS)
    x2, y2 = _gauge_point(end_fraction, GAUGE_RADIUS)
    return f"M {x1:.1f} {y1:.1f} A {GAUGE_RADIUS:.0f} {GAUGE_RADIUS:.0f} 0 0 1 {x2:.1f} {y2:.1f}"


def _tick(value, inner_radius, major):
    fraction = _gauge_fraction(value)
    x1, y1 = _gauge_point(fraction, GAUGE_TICK_OUTER_RADIUS)
    x2, y2 = _gauge_point(fraction, inner_radius)
    return {"x1": f"{x1:.1f}", "y1": f"{y1:.1f}", "x2": f"{x2:.1f}", "y2": f"{y2:.1f}", "major": major}


def _label(text, fraction, kind, key=None):
    x, y = _gauge_point(fraction, GAUGE_LABEL_RADIUS)
    return {"text": text, "x": f"{x:.1f}", "y": f"{y:.1f}", "kind": kind, "key": key}


def _build_gauge_geometry():
    gap = GAUGE_SEGMENT_GAP_DEGREES / 180
    thresholds = [category["upper"] for category in BMI_CATEGORIES[:-1]]
    bounds = [GAUGE_MIN, *thresholds, GAUGE_MAX]
    last_index = len(BMI_CATEGORIES) - 1
    segments = []
    labels = []
    for index, category in enumerate(BMI_CATEGORIES):
        lower, upper = _gauge_fraction(bounds[index]), _gauge_fraction(bounds[index + 1])
        start = lower + (gap if index > 0 else 0)
        end = upper - (gap if index < last_index else 0)
        segments.append(
            {
                "key": category["key"],
                "label": category["short_label"],
                "tone": category["tone"],
                "path": _arc_path(start, end),
            }
        )
        labels.append(_label(category["short_label"], (lower + upper) / 2, "name", category["key"]))
    labels.extend(_label(f"{value:g}", _gauge_fraction(value), "value") for value in bounds)
    ticks = [_tick(value, GAUGE_MINOR_TICK_INNER_RADIUS, False) for value in range(GAUGE_MIN, GAUGE_MAX + 1) if value not in thresholds]
    ticks.extend(_tick(value, GAUGE_MAJOR_TICK_INNER_RADIUS, True) for value in thresholds)
    tip_x, tip_y = GAUGE_CENTER_X, GAUGE_CENTER_Y - GAUGE_NEEDLE_LENGTH
    return {
        "view_box": GAUGE_VIEW_BOX,
        "center_x": f"{GAUGE_CENTER_X:g}",
        "center_y": f"{GAUGE_CENTER_Y:g}",
        "value_y": f"{GAUGE_VALUE_Y:g}",
        "needle_points": f"{GAUGE_CENTER_X - 5:g},{GAUGE_CENTER_Y:g} {tip_x:g},{tip_y:g} {GAUGE_CENTER_X + 5:g},{GAUGE_CENTER_Y:g}",
        "segments": segments,
        "ticks": ticks,
        "labels": labels,
    }


GAUGE_GEOMETRY = _build_gauge_geometry()


def bmi_gauge(bmi):
    fraction = _gauge_fraction(bmi)
    return {
        "min": GAUGE_MIN,
        "max": GAUGE_MAX,
        "needle_angle": round(-90 + 180 * fraction, 1),
        "clamped": not GAUGE_MIN <= bmi <= GAUGE_MAX,
        "active_key": bmi_guidance(bmi)["key"],
        **GAUGE_GEOMETRY,
    }


def parse_positive_number(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number > 0 else None


@app.route("/", methods=["GET", "POST"])
def index():
    name_input = ""
    height_input = ""
    weight_input = ""
    errors = {}
    result = None

    if request.method == "POST":
        # 姓名為選填：去除前後空白，並將連續空白（含換行、Tab）合併為單一空格。
        name_input = " ".join(request.form.get("name", "").split())
        height_input = request.form.get("height", "").strip()
        weight_input = request.form.get("weight", "").strip()
        height = parse_positive_number(height_input)
        weight = parse_positive_number(weight_input)

        if len(name_input) > NAME_MAX_LENGTH:
            errors["name"] = f"姓名請勿超過 {NAME_MAX_LENGTH} 個字。"
        if height is None:
            errors["height"] = "請輸入大於 0 的有效身高（公分）。"
        if weight is None:
            errors["weight"] = "請輸入大於 0 的有效體重（公斤）。"

        if not errors:
            height_meters = height / 100
            height_squared = height_meters * height_meters
            if not math.isfinite(height_squared) or height_squared == 0:
                errors["height"] = "無法使用這組數值計算 BMI，請檢查身高與體重。"
            else:
                bmi = weight / height_squared
                if not math.isfinite(bmi) or bmi == 0:
                    errors["weight"] = "無法使用這組數值計算 BMI，請檢查身高與體重。"
                else:
                    displayed_bmi = round(bmi, 1)
                    result = {
                        "name": name_input,
                        "bmi": f"{displayed_bmi:.1f}",
                        **bmi_guidance(displayed_bmi),
                        "gauge": bmi_gauge(displayed_bmi),
                    }

    return render_template(
        "index.html",
        name_input=name_input,
        name_max_length=NAME_MAX_LENGTH,
        height_input=height_input,
        weight_input=weight_input,
        errors=errors,
        result=result,
    )


if __name__ == "__main__":
    app.run(debug=True)
