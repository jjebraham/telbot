def get_form_structure():
    return {
        1: {"label": "نام", "value": None},
        2: {"label": "نام خانوادگی", "value": None},
        3: {"label": "شماره موبایل", "value": None},
        4: {"label": "کد ملی", "value": None},
        5: {"label": "تاریخ تولد", "value": None},
        6: {"label": "کارت بانکی", "value": None},
        7: {"label": "قوانین و مقررات", "value": None},
        8: {"label": "تصویر روی کارت ملی", "value": None},
        9: {"label": "تصویر پشت کارت ملی", "value": None},
    }

def render_form(data: dict, current_step: int) -> str:
    total = len(data)
    completed = sum(1 for v in data.values() if v["value"] is not None)
    bar = "🟩" * completed + "⬜" * (total - completed)
    progress = f"📊 پیشرفت: {bar} ({completed}/{total})\n\n"

    lines = []
    for step, field in data.items():
        if field["value"]:
            prefix = "🟢"
        elif step == current_step:
            prefix = "🟡"
        else:
            prefix = "🔴"
        value = field["value"] if field["value"] else ""
        lines.append(f"{prefix}{step}/{total} {field['label']}: {value}")
    return progress + "\n".join(lines)
