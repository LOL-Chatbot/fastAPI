import os
import time
from typing import Any

import gradio as gr
import requests


API_BASE_URL = os.getenv("FASTAPI_BASE_URL", "http://127.0.0.1:8000")
POSITIONS = ["TOP", "JUNGLE", "MID", "ADC", "SUPPORT"]
SPELL_CHECK_POSITIONS = [
    ("TOP", "탑"),
    ("JUNGLE", "정글"),
    ("MID", "미드"),
    ("ADC", "원딜"),
    ("SUPPORT", "서폿"),
]
FLASH_COOLDOWN_SECONDS = 300


def call_api(
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    url = f"{API_BASE_URL}{path}"
    if method == "GET":
        response = requests.get(url, timeout=60)
    else:
        response = requests.post(url, json=payload or {}, timeout=120)

    try:
        result = response.json()
    except ValueError:
        response.raise_for_status()
        raise

    if not result.get("success", False):
        error = result.get("error", {})
        raise RuntimeError(error.get("message", "정보 조회 실패"))

    response.raise_for_status()
    return result["data"]


def chat(message: str, history: list[Any]):
    response_text = ""
    try:
        with requests.post(
            f"{API_BASE_URL}/chat/stream",
            json={"message": message},
            timeout=(10, 300),
            stream=True,
        ) as response:
            response.raise_for_status()
            for chunk in response.iter_content(
                chunk_size=64,
                decode_unicode=True,
            ):
                if not chunk:
                    continue
                response_text += chunk
                yield response_text
    except requests.RequestException as exc:
        yield f"정보 조회 실패: {exc}"

    if not response_text:
        yield "정보 조회 실패: 빈 응답을 받았습니다."


def search_champions(position: str | None) -> str:
    query = f"?position={position}" if position else ""
    data = call_api("GET", f"/champions{query}")
    champions = data.get("champions", [])
    rows = ["| 챔피언 | 영문명 | 포지션 |", "| --- | --- | --- |"]

    for champion in champions[:80]:
        rows.append(
            "| {name_ko} | {name_en} | {positions} |".format(
                name_ko=champion.get("name_ko", ""),
                name_en=champion.get("name_en", ""),
                positions=", ".join(champion.get("positions", [])),
            )
        )

    suffix = ""
    if len(champions) > 80:
        suffix = f"\n\n총 {len(champions)}개 중 80개만 표시했습니다."

    return "\n".join(rows) + suffix


def recommend_build(champion_name: str, position: str) -> str:
    data = call_api(
        "POST",
        "/recommendations/champion-build",
        {
            "champion_id": champion_name.strip(),
            "position": position,
        },
    )

    runes = data.get("runes", {})
    items = data.get("items", {})
    spells = data.get("spells", [])
    skills = data.get("skills", {})
    counters = data.get("counters", [])

    sections = [
        f"## {data.get('champion_id', champion_name)} {position} 추천",
        data.get("summary", ""),
        "### 룬",
        render_runes(runes),
        "### 스펠",
        render_named_images(spells),
        "### 시작 아이템",
        render_named_images(items.get("start_items", [])),
        "### 코어 아이템",
        render_named_images(items.get("core_items", [])),
        "### 신발",
        render_named_images(items.get("boots", [])),
        "### 스킬 선마",
        render_skills(skills),
        "### 카운터",
        render_counters(counters),
    ]
    return "\n\n".join(section for section in sections if section)


def recommend_runes(champion_name: str, position: str) -> str:
    data = call_api(
        "POST",
        "/recommendations/runes",
        {
            "champion_id": champion_name.strip(),
            "position": position,
        },
    )
    return render_runes(data)


def recommend_items(champion_name: str, position: str) -> str:
    data = call_api(
        "POST",
        "/recommendations/items",
        {
            "champion_id": champion_name.strip(),
            "position": position,
        },
    )
    return "\n\n".join(
        [
            "### 시작 아이템",
            render_named_images(data.get("start_items", [])),
            "### 코어 아이템",
            render_named_images(data.get("core_items", [])),
            "### 신발",
            render_named_images(data.get("boots", [])),
        ]
    )


def render_runes(runes: dict[str, Any]) -> str:
    keystone = runes.get("keystone", {})
    keystone_image = render_image(keystone)
    primary_runes = render_named_images_inline(
        runes.get("primary_rune_images", []),
        runes.get("primary_runes", []),
    )
    secondary_runes = render_named_images_inline(
        runes.get("secondary_rune_images", []),
        runes.get("secondary_runes", []),
    )
    stat_shards = ", ".join(runes.get("stat_shards", []))

    return (
        f"**주 룬:** {runes.get('primary_style', '')}\n\n"
        f"**핵심 룬:** {keystone_image}\n\n"
        f"**세부 룬:** {primary_runes}\n\n"
        f"**보조 룬:** {runes.get('secondary_style', '')} - {secondary_runes}\n\n"
        f"**능력치 파편:** {stat_shards}"
    )


def render_named_images(values: list[dict[str, Any]]) -> str:
    if not values:
        return "표시할 데이터가 없습니다."

    return "\n\n".join(render_image(value) for value in values)


def render_named_images_inline(
    values: list[Any],
    fallback_names: list[str] | None = None,
) -> str:
    if not values:
        return ", ".join(fallback_names or [])

    rendered_values = []
    for value in values:
        if isinstance(value, dict):
            rendered_values.append(f"{render_image_tag(value)} {value.get('name', '')}")
        else:
            rendered_values.append(str(value))
    return " ".join(rendered_values)


def render_image(value: dict[str, Any], size: int = 32) -> str:
    name = value.get("name", "")
    image_tag = render_image_tag(value, size)
    if image_tag == name:
        return name

    return f"{image_tag}\n\n{name}"


def render_image_tag(value: dict[str, Any], size: int = 32) -> str:
    name = value.get("name", "")
    image = value.get("image") or {}
    image_url = image.get("image_url")
    if not image_url:
        return name

    return (
        f'<img src="{image_url}" alt="{name}" '
        f'width="{size}" height="{size}" '
        'style="vertical-align:middle;border-radius:6px;object-fit:cover;">'
    )


def render_skills(skills: dict[str, Any]) -> str:
    priority_images = skills.get("priority_images", [])
    if priority_images:
        images = " ".join(render_image(skill) for skill in priority_images)
        names = " > ".join(skill.get("name", "") for skill in priority_images)
        return f"{images}\n\n{names}\n\n{skills.get('description', '')}"

    return f"{' > '.join(skills.get('priority', []))}\n\n{skills.get('description', '')}"


def render_counters(counters: list[dict[str, Any]]) -> str:
    if not counters:
        return "표시할 데이터가 없습니다."

    rows = ["| 챔피언 | 이유 |", "| --- | --- |"]
    for counter in counters:
        rows.append(
            f"| {counter.get('name_ko', '')} | {counter.get('reason', '')} |"
        )
    return "\n".join(rows)


def create_spell_timer_state() -> dict[str, Any]:
    return {
        "running": False,
        "elapsed_base": 0.0,
        "started_at": None,
        "spell_used_at": {position: None for position, _ in SPELL_CHECK_POSITIONS},
    }


def get_game_seconds(state: dict[str, Any] | None) -> int:
    if not state:
        return 0

    elapsed = float(state.get("elapsed_base") or 0)
    if state.get("running") and state.get("started_at") is not None:
        elapsed += time.monotonic() - float(state["started_at"])
    return max(0, int(elapsed))


def format_game_time(seconds: int | float | None) -> str:
    if seconds is None:
        return "-"

    seconds = max(0, int(seconds))
    minutes, remain_seconds = divmod(seconds, 60)
    return f"{minutes:02d}:{remain_seconds:02d}"


def render_spell_timer(state: dict[str, Any] | None) -> str:
    state = state or create_spell_timer_state()
    game_seconds = get_game_seconds(state)
    status = "진행 중" if state.get("running") else "대기 중"
    rows = [
        f"## 현재 게임 시간 `{format_game_time(game_seconds)}`",
        f"상태: **{status}**",
        "",
        "| 포지션 | 점멸 상태 | 사용 시점 | 재사용 가능 시간 | 남은 시간 |",
        "| --- | --- | --- | --- | --- |",
    ]

    spell_used_at = state.get("spell_used_at", {})
    for position, label in SPELL_CHECK_POSITIONS:
        used_at = spell_used_at.get(position)
        if used_at is None:
            rows.append(f"| {label} | 사용 가능 | - | - | 00:00 |")
            continue

        available_at = int(used_at) + FLASH_COOLDOWN_SECONDS
        remaining = max(0, available_at - game_seconds)
        spell_status = "쿨다운 중" if remaining > 0 else "사용 가능"
        rows.append(
            "| {label} | {status} | {used_at} | {available_at} | {remaining} |".format(
                label=label,
                status=spell_status,
                used_at=format_game_time(used_at),
                available_at=format_game_time(available_at),
                remaining=format_game_time(remaining),
            )
        )

    return "\n".join(rows)


def start_spell_timer(
    state: dict[str, Any] | None,
) -> tuple[dict[str, Any], str]:
    state = state or create_spell_timer_state()
    if not state.get("running"):
        state = {
            **state,
            "running": True,
            "started_at": time.monotonic(),
        }
    return state, render_spell_timer(state)


def reset_spell_timer() -> tuple[dict[str, Any], str]:
    state = create_spell_timer_state()
    return state, render_spell_timer(state)


def record_flash_use(
    position: str,
    state: dict[str, Any] | None,
) -> tuple[dict[str, Any], str]:
    state = state or create_spell_timer_state()
    if not state.get("running"):
        return state, render_spell_timer(state)

    spell_used_at = dict(state.get("spell_used_at", {}))
    spell_used_at[position] = get_game_seconds(state)
    state = {**state, "spell_used_at": spell_used_at}
    return state, render_spell_timer(state)


def cancel_flash_use(
    position: str,
    state: dict[str, Any] | None,
) -> tuple[dict[str, Any], str]:
    state = state or create_spell_timer_state()
    spell_used_at = dict(state.get("spell_used_at", {}))
    spell_used_at[position] = None
    state = {**state, "spell_used_at": spell_used_at}
    return state, render_spell_timer(state)


def refresh_spell_timer(
    state: dict[str, Any] | None,
) -> tuple[dict[str, Any], str]:
    state = state or create_spell_timer_state()
    return state, render_spell_timer(state)


with gr.Blocks(title="LOL 챗봇 MVP") as demo:
    gr.Markdown("# LOL 챗봇 MVP")

    with gr.Tab("챗봇"):
        gr.ChatInterface(
            fn=chat,
            chatbot=gr.Chatbot(height=420),
            textbox=gr.Textbox(
                placeholder="케이틀린 원딜 빌드 알려줘",
            ),
            examples=[
                "징크스 원딜 룬이랑 아이템 추천해줘",
                "케이틀린 ADC 빌드 알려줘",
                "아리 미드 카운터 알려줘",
            ],
        )

    with gr.Tab("종합 빌드"):
        build_champion = gr.Textbox(label="챔피언 이름", value="케이틀린")
        build_position = gr.Dropdown(label="포지션", choices=POSITIONS, value="ADC")
        build_output = gr.Markdown()
        gr.Button("추천 조회").click(
            recommend_build,
            inputs=[build_champion, build_position],
            outputs=build_output,
        )

    with gr.Tab("룬"):
        rune_champion = gr.Textbox(label="챔피언 이름", value="케이틀린")
        rune_position = gr.Dropdown(label="포지션", choices=POSITIONS, value="ADC")
        rune_output = gr.Markdown()
        gr.Button("룬 조회").click(
            recommend_runes,
            inputs=[rune_champion, rune_position],
            outputs=rune_output,
        )

    with gr.Tab("아이템"):
        item_champion = gr.Textbox(label="챔피언 이름", value="케이틀린")
        item_position = gr.Dropdown(label="포지션", choices=POSITIONS, value="ADC")
        item_output = gr.Markdown()
        gr.Button("아이템 조회").click(
            recommend_items,
            inputs=[item_champion, item_position],
            outputs=item_output,
        )

    with gr.Tab("챔피언 목록"):
        champion_position = gr.Dropdown(
            label="포지션",
            choices=[""] + POSITIONS,
            value="",
        )
        champion_output = gr.Markdown()
        gr.Button("목록 조회").click(
            search_champions,
            inputs=champion_position,
            outputs=champion_output,
        )


    with gr.Tab("상대 스펠 체크"):
        spell_timer_state = gr.State(create_spell_timer_state())
        spell_timer = gr.Timer(1)
        spell_output = gr.Markdown(render_spell_timer(create_spell_timer_state()))

        with gr.Row():
            gr.Button("게임 시작").click(
                start_spell_timer,
                inputs=spell_timer_state,
                outputs=[spell_timer_state, spell_output],
            )
            gr.Button("초기화").click(
                reset_spell_timer,
                outputs=[spell_timer_state, spell_output],
            )

        with gr.Row():
            for position, label in SPELL_CHECK_POSITIONS:
                with gr.Column():
                    gr.Button(f"{label} 점멸 사용").click(
                        record_flash_use,
                        inputs=[gr.State(position), spell_timer_state],
                        outputs=[spell_timer_state, spell_output],
                    )
                    gr.Button(f"{label} 취소").click(
                        cancel_flash_use,
                        inputs=[gr.State(position), spell_timer_state],
                        outputs=[spell_timer_state, spell_output],
                    )

        spell_timer.tick(
            refresh_spell_timer,
            inputs=spell_timer_state,
            outputs=[spell_timer_state, spell_output],
        )


if __name__ == "__main__":
    demo.launch()
