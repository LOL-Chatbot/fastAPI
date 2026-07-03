import os
from dataclasses import dataclass

from dotenv import load_dotenv
from google import genai
from google.genai.client import Client


load_dotenv()


@dataclass(frozen=True)
class LlmPromptConfig:
    system_prompt: str = (
        "너는 리그 오브 레전드 챔피언 플레이 질문에 답하는 한국어 챗봇이다. "
        "반드시 OP.GG MCP에서 조회된 데이터만 근거로 답변한다. "
        "조회 데이터에 없는 내용은 추측하지 말고 확인할 수 없다고 말한다. "
        "사용자가 빌드, 룬, 아이템, 스킬, 카운터, 라인 메타, 추천 픽, 시너지, "
        "라인전 매치업, 챔피언 스킬/팁/기본 정보, 장인/랭커 정보를 물으면 "
        "제공된 조회 데이터의 범위 안에서만 답변한다. "
        "사용자가 상대 조합, 우리팀 조합, 특정 라인 상대, 마지막 픽 추천을 물으면 "
        "라인 메타, 상대 챔피언의 카운터 데이터, 아군 챔피언의 시너지 데이터를 함께 비교해 "
        "가장 근거가 강한 후보를 추천한다."
    )
    answer_template: str = (
        "{system_prompt}\n\n"
        "[사용자 질문]\n"
        "{message}\n\n"
        "[추천 데이터]\n"
        "- 챔피언: {champion_id}\n"
        "- 포지션: {position}\n"
        "- 룬: {primary_style} / {keystone}\n"
        "- 보조 룬: {secondary_style}\n"
        "- 스펠: {spells}\n"
        "- 시작 아이템: {start_items}\n"
        "- 핵심 아이템: {core_items}\n"
        "- 스킬 선마: {skills}\n"
        "- 주의할 상대: {counters}\n\n"
        "위 데이터만 근거로 초보자도 이해하기 쉽게 3~5문장으로 답변해줘."
    )
    retrieval_answer_template: str = (
        "{system_prompt}\n\n"
        "[사용자 질문]\n"
        "{message}\n\n"
        "[질문 유형]\n"
        "{question_type}\n\n"
        "[사용한 OP.GG MCP 도구]\n"
        "{tool_name}\n\n"
        "[조회 조건]\n"
        "{query_context}\n\n"
        "[조회 데이터]\n"
        "{retrieved_data}\n\n"
        "답변 규칙:\n"
        "1. 위 조회 데이터에 있는 내용만 근거로 답변한다.\n"
        "2. 데이터에 없는 챔피언, 수치, 운영법은 추측하지 않는다.\n"
        "3. 사용자의 질문 유형에 직접 답한다.\n"
        "4. 추천이 필요한 경우 승률, 픽률, 티어, 카운터, 시너지, 표본 등 "
        "조회 데이터에 있는 근거를 함께 언급한다.\n"
        "5. 조합 추천 질문에서는 먼저 1~3개 후보를 제시하고, 각 후보마다 "
        "메타 근거와 카운터/시너지 근거를 구분해 설명한다.\n"
        "6. 서로 충돌하는 데이터가 있으면 표본 수, 티어, 승률이 더 분명한 근거를 우선한다.\n"
        "7. 카운터 질문에서 win_rate는 분석 대상 챔피언의 상대전 승률이다. "
        "따라서 win_rate가 낮은 상대만 카운터로 답하고, win_rate가 높은 상대는 "
        "상대하기 쉬운 챔피언으로 분류한다.\n"
        "8. 시너지 질문에서는 조합 승률 win_rate와 조합 표본 play/play_share를 우선 근거로 삼고, "
        "synergy_tier_data는 OP.GG가 반환한 시너지 챔피언의 포지션 티어/랭크 보조 근거로만 설명한다.\n"
        "9. 한국어로 3~8문장 안에서 간결하게 답한다."
    )


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str | None
    gemini_model: str
    gemini_temperature: float
    opgg_mcp_dir: str
    data_dragon_version: str | None
    data_dragon_language: str
    llm_prompts: LlmPromptConfig


def get_settings() -> Settings:
    return Settings(
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        gemini_temperature=float(os.getenv("GEMINI_TEMPERATURE", "0.1")),
        opgg_mcp_dir=os.getenv(
            "OPGG_MCP_DIR",
            r"C:\Users\jinwo\Documents\opgg\opgg-mcp",
        ),
        data_dragon_version=os.getenv("DATA_DRAGON_VERSION") or None,
        data_dragon_language=os.getenv("DATA_DRAGON_LANGUAGE", "ko_KR"),
        llm_prompts=LlmPromptConfig(),
    )


def create_llm_client(settings: Settings) -> Client | None:
    if not settings.gemini_api_key:
        return None

    return genai.Client(api_key=settings.gemini_api_key)


def build_chat_prompt(
    settings: Settings,
    message: str,
    champion_id: str,
    position: str,
    primary_style: str,
    keystone: str,
    secondary_style: str,
    spells: list[str],
    start_items: list[str],
    core_items: list[str],
    skills: list[str],
    counters: list[str],
) -> str:
    prompts = settings.llm_prompts
    return prompts.answer_template.format(
        system_prompt=prompts.system_prompt,
        message=message,
        champion_id=champion_id,
        position=position,
        primary_style=primary_style,
        keystone=keystone,
        secondary_style=secondary_style,
        spells=", ".join(spells),
        start_items=", ".join(start_items),
        core_items=", ".join(core_items),
        skills=" > ".join(skills),
        counters=", ".join(counters),
    )


def build_retrieval_chat_prompt(
    settings: Settings,
    message: str,
    question_type: str,
    tool_name: str,
    query_context: str,
    retrieved_data: str,
) -> str:
    prompts = settings.llm_prompts
    return prompts.retrieval_answer_template.format(
        system_prompt=prompts.system_prompt,
        message=message,
        question_type=question_type,
        tool_name=tool_name,
        query_context=query_context,
        retrieved_data=retrieved_data,
    )
