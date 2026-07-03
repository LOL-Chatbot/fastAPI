from collections.abc import Iterator
from typing import Any

from google.genai import types
from google.genai.client import Client

from app.core.config import (
    Settings,
    build_chat_prompt,
    build_retrieval_chat_prompt,
    create_llm_client,
    get_settings,
)
from app.schemas.chat import ChatData, RelatedChampion
from app.schemas.common import Position
from app.schemas.recommendation import ChampionBuildData, NamedImage
from app.services.recommendation_service import RecommendationService


class LlmService:
    def __init__(
        self,
        settings: Settings | None = None,
        llm_client: Client | None = None,
        recommendation_service: RecommendationService | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._llm_client = llm_client or create_llm_client(self._settings)
        self._recommendation_service = recommendation_service or RecommendationService(
            settings=self._settings
        )

    def create_answer(
        self,
        message: str,
        champion_id: str | None = None,
        position: Position | None = None,
    ) -> ChatData:
        champion_mentions = self._find_champion_mentions(message)
        detected_champions = [
            str(mention["champion_id"])
            for mention in champion_mentions
        ]
        resolved_champion_id = (
            self._recommendation_service.resolve_champion_id(champion_id)
            if champion_id
            else (detected_champions[0] if detected_champions else None)
        )
        resolved_position = position or self._find_target_position(message)
        route = self._classify_question(
            message=message,
            champion_ids=(
                [resolved_champion_id]
                if resolved_champion_id and not detected_champions
                else detected_champions
            ),
            position=resolved_position,
            champion_mentions=champion_mentions,
        )

        if route == "champion_build" and resolved_champion_id and resolved_position:
            return self._create_build_answer(
                message=message,
                champion_id=resolved_champion_id,
                position=resolved_position,
            )

        if route != "missing_context":
            return self._create_retrieval_answer(
                message=message,
                route=route,
                champion_ids=(
                    [resolved_champion_id]
                    if resolved_champion_id and not detected_champions
                    else detected_champions
                ),
                position=resolved_position,
                champion_mentions=champion_mentions,
            )

        missing_context_message = self._build_missing_context_message(
            message=message,
            champion_id=resolved_champion_id,
            position=resolved_position,
        )
        return ChatData(
            answer=missing_context_message,
            related_champions=[],
        )

    def create_answer_stream(
        self,
        message: str,
        champion_id: str | None = None,
        position: Position | None = None,
    ) -> Iterator[str]:
        yield "OP.GG 데이터 조회 중...\n\n"

        champion_mentions = self._find_champion_mentions(message)
        detected_champions = [
            str(mention["champion_id"])
            for mention in champion_mentions
        ]
        resolved_champion_id = (
            self._recommendation_service.resolve_champion_id(champion_id)
            if champion_id
            else (detected_champions[0] if detected_champions else None)
        )
        resolved_position = position or self._find_target_position(message)
        route = self._classify_question(
            message=message,
            champion_ids=(
                [resolved_champion_id]
                if resolved_champion_id and not detected_champions
                else detected_champions
            ),
            position=resolved_position,
            champion_mentions=champion_mentions,
        )

        if route == "missing_context":
            yield self._build_missing_context_message(
                message=message,
                champion_id=resolved_champion_id,
                position=resolved_position,
            )
            return

        try:
            prompt, fallback_answer, visual_summary = self._build_stream_prompt(
                message=message,
                route=route,
                champion_id=resolved_champion_id,
                champion_ids=(
                    [resolved_champion_id]
                    if resolved_champion_id and not detected_champions
                    else detected_champions
                ),
                position=resolved_position,
                champion_mentions=champion_mentions,
            )
        except Exception as exc:
            yield (
                "OP.GG MCP에서 질문에 맞는 챔피언 정보를 조회하지 못했습니다.\n\n"
                f"상세: {exc}"
            )
            return

        yield "OP.GG 데이터 조회 완료. 답변 생성 중...\n\n"

        has_generated_text = False
        for chunk in self._generate_answer_stream(prompt):
            has_generated_text = True
            yield chunk

        if not has_generated_text:
            yield fallback_answer

        if visual_summary:
            yield f"\n\n---\n\n{visual_summary}"

    def _build_stream_prompt(
        self,
        message: str,
        route: str,
        champion_id: str | None,
        champion_ids: list[str],
        position: Position | None,
        champion_mentions: list[dict[str, Any]],
    ) -> tuple[str, str, str]:
        if route == "champion_build" and champion_id and position:
            build = self._recommendation_service.get_champion_build(
                champion_id=champion_id,
                position=position,
            )
            spell_names = [spell.name for spell in build.spells]
            start_item_names = [item.name for item in build.items.start_items]
            core_item_names = [item.name for item in build.items.core_items]
            counter_names = [counter.name_ko for counter in build.counters]
            prompt = build_chat_prompt(
                settings=self._settings,
                message=message,
                champion_id=build.champion_id,
                position=position.value,
                primary_style=build.runes.primary_style,
                keystone=build.runes.keystone.name,
                secondary_style=build.runes.secondary_style,
                spells=spell_names,
                start_items=start_item_names,
                core_items=core_item_names,
                skills=build.skills.priority,
                counters=counter_names,
            )
            fallback_answer = self._build_fallback_answer(
                message=message,
                build=build,
                spell_names=spell_names,
                start_item_names=start_item_names,
                core_item_names=core_item_names,
                counter_names=counter_names,
            )
            return prompt, fallback_answer, self._render_visual_build_summary(build)

        retrieval = self._retrieve_context(
            route=route,
            champion_ids=champion_ids,
            position=position,
            message=message,
            champion_mentions=champion_mentions,
        )
        prompt = build_retrieval_chat_prompt(
            settings=self._settings,
            message=message,
            question_type=retrieval["question_type"],
            tool_name=retrieval["tool_name"],
            query_context=retrieval["query_context"],
            retrieved_data=self._limit_text(retrieval["retrieved_data"]),
        )
        return prompt, self._build_retrieval_fallback_answer(retrieval), ""

    def _create_build_answer(
        self,
        message: str,
        champion_id: str,
        position: Position,
    ) -> ChatData:
        build = self._recommendation_service.get_champion_build(
            champion_id=champion_id,
            position=position,
        )
        spell_names = [spell.name for spell in build.spells]
        start_item_names = [item.name for item in build.items.start_items]
        core_item_names = [item.name for item in build.items.core_items]
        counter_names = [counter.name_ko for counter in build.counters]
        prompt = build_chat_prompt(
            settings=self._settings,
            message=message,
            champion_id=build.champion_id,
            position=position.value,
            primary_style=build.runes.primary_style,
            keystone=build.runes.keystone.name,
            secondary_style=build.runes.secondary_style,
            spells=spell_names,
            start_items=start_item_names,
            core_items=core_item_names,
            skills=build.skills.priority,
            counters=counter_names,
        )
        generated_answer = self._generate_answer(prompt)
        answer = generated_answer or self._build_fallback_answer(
            message=message,
            build=build,
            spell_names=spell_names,
            start_item_names=start_item_names,
            core_item_names=core_item_names,
            counter_names=counter_names,
        )
        visual_summary = self._render_visual_build_summary(build)

        return ChatData(
            answer=f"{answer}\n\n---\n\n{visual_summary}",
            related_champions=[
                RelatedChampion(
                    champion_id=build.champion_id,
                    name_ko=build.champion_id,
                )
            ],
        )

    def _create_retrieval_answer(
        self,
        message: str,
        route: str,
        champion_ids: list[str],
        position: Position | None,
        champion_mentions: list[dict[str, Any]],
    ) -> ChatData:
        try:
            retrieval = self._retrieve_context(
                route=route,
                champion_ids=champion_ids,
                position=position,
                message=message,
                champion_mentions=champion_mentions,
            )
        except Exception:
            return ChatData(
                answer="OP.GG MCP에서 질문에 맞는 챔피언 정보를 조회하지 못했습니다.",
                related_champions=self._build_related_champions(champion_ids),
            )

        prompt = build_retrieval_chat_prompt(
            settings=self._settings,
            message=message,
            question_type=retrieval["question_type"],
            tool_name=retrieval["tool_name"],
            query_context=retrieval["query_context"],
            retrieved_data=self._limit_text(retrieval["retrieved_data"]),
        )
        generated_answer = self._generate_answer(prompt)
        answer = generated_answer or self._build_retrieval_fallback_answer(
            retrieval=retrieval,
        )

        return ChatData(
            answer=answer,
            related_champions=self._build_related_champions(champion_ids),
        )

    def _retrieve_context(
        self,
        route: str,
        champion_ids: list[str],
        position: Position | None,
        message: str,
        champion_mentions: list[dict[str, Any]],
    ) -> dict[str, str]:
        if route == "pick_recommendation" and position:
            return self._retrieve_pick_recommendation_context(
                message=message,
                position=position,
                champion_mentions=champion_mentions,
            )

        if route == "lane_meta" and position:
            return {
                "question_type": "라인 메타/추천 픽",
                "tool_name": "lol_list_lane_meta_champions",
                "query_context": f"포지션={position.value}",
                "retrieved_data": self._recommendation_service.get_lane_meta_context(
                    position
                ),
            }

        if route == "champion_synergy" and champion_ids:
            synergy_query = self._resolve_synergy_query(
                message=message,
                champion_ids=champion_ids,
                position=position,
                champion_mentions=champion_mentions,
            )
            if synergy_query is None:
                raise ValueError("시너지 조회 조건을 찾지 못했습니다.")

            return {
                "question_type": "챔피언 시너지",
                "tool_name": "lol_get_champion_synergies",
                "query_context": (
                    f"기준 챔피언={synergy_query['champion_id']}, "
                    f"기준 챔피언 포지션={synergy_query['my_position'].value}, "
                    f"추천받을 시너지 포지션={synergy_query['synergy_position'].value}"
                ),
                "retrieved_data": (
                    self._recommendation_service.get_champion_synergy_context(
                        champion_id=str(synergy_query["champion_id"]),
                        my_position=synergy_query["my_position"],
                        synergy_position=synergy_query["synergy_position"],
                    )
                ),
            }

        if route == "lane_matchup" and len(champion_ids) >= 2 and position:
            return {
                "question_type": "라인전 매치업",
                "tool_name": "lol_get_lane_matchup_guide",
                "query_context": (
                    f"내 챔피언={champion_ids[0]}, 상대 챔피언={champion_ids[1]}, "
                    f"포지션={position.value}"
                ),
                "retrieved_data": (
                    self._recommendation_service.get_lane_matchup_context(
                        my_champion_id=champion_ids[0],
                        opponent_champion_id=champion_ids[1],
                        position=position,
                    )
                ),
            }

        if route == "champion_detail" and champion_ids:
            return {
                "question_type": "챔피언 기본 정보/스킬/팁",
                "tool_name": "lol_list_champion_details",
                "query_context": f"챔피언={', '.join(champion_ids[:10])}",
                "retrieved_data": self._recommendation_service.get_champion_detail_context(
                    champion_ids
                ),
            }

        if route == "champion_leaderboard" and champion_ids:
            return {
                "question_type": "챔피언 장인/리더보드",
                "tool_name": "lol_list_champion_leaderboard",
                "query_context": f"지역=KR, 챔피언={champion_ids[0]}",
                "retrieved_data": (
                    self._recommendation_service.get_champion_leaderboard_context(
                        champion_ids[0],
                        region="KR",
                    )
                ),
            }

        if route == "counter_pick" and champion_ids and position:
            def build_analysis_context(champion_id: str) -> str:
                analysis_context = (
                    self._recommendation_service.get_champion_analysis_context(
                        champion_id=champion_id,
                        position=position,
                    )
                )
                return f"[분석 대상 챔피언: {champion_id}]\n{analysis_context}"

            return {
                "question_type": "상대 챔피언 기준 카운터/추천 픽",
                "tool_name": "lol_get_champion_analysis",
                "query_context": (
                    f"상대 또는 기준 챔피언={', '.join(champion_ids)}, "
                    f"포지션={position.value}. "
                    "win_rate는 분석 대상 챔피언의 상대전 승률입니다. "
                    "카운터는 분석 대상 챔피언의 win_rate가 낮은 상대입니다. "
                    "win_rate가 높은 상대는 카운터가 아니라 상대하기 쉬운 챔피언입니다."
                ),
                "retrieved_data": "\n\n".join(
                    build_analysis_context(champion_id)
                    for champion_id in champion_ids[:5]
                ),
            }

        if champion_ids and position:
            return {
                "question_type": "챔피언 분석",
                "tool_name": "lol_get_champion_analysis",
                "query_context": f"챔피언={champion_ids[0]}, 포지션={position.value}",
                "retrieved_data": (
                    self._recommendation_service.get_champion_analysis_context(
                        champion_id=champion_ids[0],
                        position=position,
                    )
                ),
            }

        raise ValueError("질문에 필요한 조회 조건이 부족합니다.")

    def _find_champions(self, message: str) -> list[str]:
        return self._recommendation_service.find_champions_in_text(message)

    def _find_champion_mentions(self, message: str) -> list[dict[str, Any]]:
        return self._recommendation_service.find_champion_mentions_in_text(message)

    def _find_position(self, message: str) -> Position | None:
        normalized_message = message.lower().replace(" ", "")
        for position, aliases in self._position_aliases().items():
            if any(alias in normalized_message for alias in aliases):
                return position

        return None

    def _find_target_position(self, message: str) -> Position | None:
        normalized_message = message.lower().replace(" ", "")
        self_markers = ["나는", "내가", "난", "저는", "제가", "나"]
        marker_indexes = [
            normalized_message.rfind(marker)
            for marker in self_markers
            if normalized_message.rfind(marker) >= 0
        ]
        if marker_indexes:
            marker_index = max(marker_indexes)
            trailing_message = normalized_message[marker_index:]
            for position, aliases in self._position_aliases().items():
                if any(alias in trailing_message for alias in aliases):
                    return position

            if len(self._find_position_mentions(message)) > 1:
                return None

        return self._find_position(message)

    def _find_positions(self, message: str) -> list[Position]:
        normalized_message = message.lower().replace(" ", "")
        return [
            position
            for position, aliases in self._position_aliases().items()
            if any(alias in normalized_message for alias in aliases)
        ]

    def _find_synergy_position(
        self,
        message: str,
        my_position: Position,
    ) -> Position:
        positions = [
            position
            for position in self._find_positions(message)
            if position != my_position
        ]
        if positions:
            return positions[0]

        if my_position == Position.ADC:
            return Position.SUPPORT
        if my_position == Position.SUPPORT:
            return Position.ADC
        return Position.JUNGLE

    def _resolve_synergy_query(
        self,
        message: str,
        champion_ids: list[str],
        position: Position | None,
        champion_mentions: list[dict[str, Any]] | None,
    ) -> dict[str, Any] | None:
        if not champion_ids:
            return None

        mentions = champion_mentions or []
        mention_contexts = self._build_mention_contexts(message, mentions)
        primary_context = mention_contexts[0] if mention_contexts else {}
        position_mentions = self._find_position_mentions(message)
        champion_index = int(primary_context.get("index", 0))
        champion_position = primary_context.get("position")
        if not isinstance(champion_position, Position):
            champion_position = self._infer_nearest_mention_position(
                position_mentions,
                champion_index,
            )

        synergy_position = position or self._find_target_position(message)
        if champion_position is None and synergy_position is not None:
            champion_position = self._default_partner_position(synergy_position)
        if synergy_position is None and champion_position is not None:
            synergy_position = self._find_synergy_position(message, champion_position)

        if (
            champion_position is None
            or synergy_position is None
            or champion_position == synergy_position
        ):
            return None

        return {
            "champion_id": str(primary_context.get("champion_id", champion_ids[0])),
            "my_position": champion_position,
            "synergy_position": synergy_position,
        }

    def _default_partner_position(self, position: Position) -> Position | None:
        if position == Position.ADC:
            return Position.SUPPORT
        if position == Position.SUPPORT:
            return Position.ADC
        return None

    def _is_synergy_question(
        self,
        normalized_message: str,
        champion_ids: list[str],
        position: Position | None,
        champion_mentions: list[dict[str, Any]] | None,
        message: str,
    ) -> bool:
        if not champion_ids:
            return False

        has_synergy_word = self._has_any(
            normalized_message,
            [
                "시너지",
                "어울",
                "조합",
                "듀오",
                "잘맞",
                "맞는",
                "같이",
                "함께",
            ],
        )
        has_ally_pick_pattern = (
            len(champion_ids) == 1
            and self._has_any(
                normalized_message,
                ["우리팀", "아군", "같은팀", "팀", "인데", "이랑", "랑"],
            )
            and self._has_any(
                normalized_message,
                ["뭐할까", "뭐픽", "뭐하지", "추천", "챔추천", "픽추천"],
            )
        )
        if not has_synergy_word and not has_ally_pick_pattern:
            return False

        return (
            self._resolve_synergy_query(
                message=message,
                champion_ids=champion_ids,
                position=position,
                champion_mentions=champion_mentions,
            )
            is not None
        )

    def _classify_question(
        self,
        message: str,
        champion_ids: list[str],
        position: Position | None,
        champion_mentions: list[dict[str, Any]] | None = None,
    ) -> str:
        normalized_message = message.lower().replace(" ", "")
        has_champion = bool(champion_ids)

        if self._is_synergy_question(
            normalized_message=normalized_message,
            champion_ids=champion_ids,
            position=position,
            champion_mentions=champion_mentions,
            message=message,
        ):
            return "champion_synergy"

        if self._has_any(
            normalized_message,
            [
                "뭐픽",
                "무슨챔",
                "어떤챔",
                "뭘픽",
                "뭐할까",
                "픽추천",
                "추천픽",
                "후픽",
                "마지막픽",
                "조합이",
                "조합인데",
            ],
        ):
            return "pick_recommendation" if position else "missing_context"

        if self._has_any(normalized_message, ["장인", "랭커", "리더보드", "고수"]):
            return "champion_leaderboard" if has_champion else "missing_context"

        if self._has_any(normalized_message, ["시너지", "어울", "조합", "듀오"]):
            if has_champion and position:
                return "champion_synergy"
            return "missing_context"

        if (
            self._has_any(normalized_message, ["상대법", "라인전", "매치업", "상대할때"])
            and len(champion_ids) >= 2
            and position
        ):
            return "lane_matchup"

        if self._has_any(
            normalized_message,
            ["스킬설명", "스킬정보", "패시브", "난이도", "팁", "스토리", "기본정보"],
        ):
            return "champion_detail" if has_champion else "missing_context"

        if self._has_any(
            normalized_message,
            ["메타", "티어", "좋은챔", "좋은픽", "추천픽", "뭐가좋", "뭐할까"],
        ):
            if position and (
                not has_champion
                or self._has_any(normalized_message, ["메타", "티어", "추천픽"])
            ):
                return "lane_meta"

        if self._has_any(
            normalized_message,
            ["카운터", "상대조합", "상대로", "상대에", "픽하면", "픽할까"],
        ):
            if has_champion and position:
                return "counter_pick"
            if position:
                return "lane_meta"
            return "missing_context"

        if has_champion and position:
            return "champion_build"

        if has_champion:
            return "champion_detail"

        if position:
            return "lane_meta"

        return "missing_context"

    def _has_any(self, value: str, keywords: list[str]) -> bool:
        return any(keyword in value for keyword in keywords)

    def _retrieve_pick_recommendation_context(
        self,
        message: str,
        position: Position,
        champion_mentions: list[dict[str, Any]],
    ) -> dict[str, str]:
        mention_contexts = self._build_mention_contexts(message, champion_mentions)
        context_parts = [
            "[내가 고를 포지션의 라인 메타 후보]\n"
            f"{self._recommendation_service.get_lane_meta_context(position)}"
        ]

        enemy_mentions = [
            mention
            for mention in mention_contexts
            if mention["side"] in {"enemy", "unknown"}
        ]
        ally_mentions = [
            mention
            for mention in mention_contexts
            if mention["side"] == "ally"
        ]

        for mention in enemy_mentions[:5]:
            champion_id = str(mention["champion_id"])
            context_parts.append(
                "[상대 챔피언 카운터 근거]\n"
                f"상대 또는 기준 챔피언={champion_id}, 기준 포지션={position.value}\n"
                "win_rate는 이 챔피언의 상대전 승률입니다. "
                "카운터는 이 챔피언의 win_rate가 낮은 상대입니다. "
                "win_rate가 높은 상대는 카운터로 추천하지 않습니다.\n"
                f"{self._recommendation_service.get_champion_analysis_context(
                    champion_id=champion_id,
                    position=position,
                )}"
            )

        for mention in ally_mentions[:5]:
            champion_id = str(mention["champion_id"])
            ally_position = mention.get("position")
            if not isinstance(ally_position, Position) or ally_position == position:
                continue

            context_parts.append(
                "[아군 챔피언 시너지 근거]\n"
                f"아군 챔피언={champion_id}, 아군 포지션={ally_position.value}, "
                f"내 포지션={position.value}\n"
                f"{self._recommendation_service.get_champion_synergy_context(
                    champion_id=champion_id,
                    my_position=ally_position,
                    synergy_position=position,
                )}"
            )

        if not ally_mentions and not enemy_mentions:
            context_parts.append(
                "[추가 설명]\n"
                "질문에서 특정 아군 또는 상대 챔피언을 찾지 못해 라인 메타 데이터만 조회했습니다."
            )

        return {
            "question_type": "조합/상대 기반 챔피언 픽 추천",
            "tool_name": (
                "lol_list_lane_meta_champions + "
                "lol_get_champion_analysis + "
                "lol_get_champion_synergies"
            ),
            "query_context": (
                f"사용자 질문={message}\n"
                f"내 포지션={position.value}\n"
                f"문장 내 챔피언 문맥={mention_contexts}"
            ),
            "retrieved_data": "\n\n".join(context_parts),
        }

    def _build_mention_contexts(
        self,
        message: str,
        champion_mentions: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        position_mentions = self._find_position_mentions(message)
        normalized_message = message.lower().replace(" ", "")

        contexts = []
        for mention in champion_mentions:
            index = int(mention["index"])
            contexts.append(
                {
                    "champion_id": mention["champion_id"],
                    "index": index,
                    "side": self._infer_mention_side(normalized_message, index),
                    "position": self._infer_mention_position(position_mentions, index),
                }
            )
        return contexts

    def _find_position_mentions(self, message: str) -> list[dict[str, Any]]:
        normalized_message = message.lower().replace(" ", "")
        mentions = []
        for position, aliases in self._position_aliases().items():
            for alias in aliases:
                start = 0
                while True:
                    index = normalized_message.find(alias, start)
                    if index < 0:
                        break
                    mentions.append(
                        {
                            "position": position,
                            "index": index,
                            "alias": alias,
                        }
                    )
                    start = index + len(alias)

        mentions.sort(key=lambda item: int(item["index"]))
        return mentions

    def _infer_mention_position(
        self,
        position_mentions: list[dict[str, Any]],
        champion_index: int,
    ) -> Position | None:
        nearest = self._infer_nearest_mention_position(
            position_mentions,
            champion_index,
        )
        if nearest is not None:
            return nearest

        return None

    def _infer_nearest_mention_position(
        self,
        position_mentions: list[dict[str, Any]],
        champion_index: int,
    ) -> Position | None:
        nearby_mentions = [
            mention
            for mention in position_mentions
            if abs(int(mention["index"]) - champion_index) <= 18
        ]
        if not nearby_mentions:
            return None

        nearby_mentions.sort(
            key=lambda mention: abs(int(mention["index"]) - champion_index)
        )
        nearest = nearby_mentions[0]
        position = nearest["position"]
        return position if isinstance(position, Position) else None

    def _infer_mention_side(self, normalized_message: str, champion_index: int) -> str:
        side_markers = [
            ("enemy", "상대팀"),
            ("enemy", "상대"),
            ("enemy", "적팀"),
            ("enemy", "적"),
            ("enemy", "상대로"),
            ("ally", "우리팀"),
            ("ally", "아군"),
            ("ally", "우리"),
            ("ally", "같은팀"),
        ]
        marker_matches = [
            (normalized_message.rfind(marker, 0, champion_index), side)
            for side, marker in side_markers
            if normalized_message.rfind(marker, 0, champion_index) >= 0
        ]
        if not marker_matches:
            return "unknown"

        marker_matches.sort(key=lambda item: item[0], reverse=True)
        return marker_matches[0][1]

    def _position_aliases(self) -> dict[Position, list[str]]:
        return {
            Position.TOP: ["top", "탑"],
            Position.JUNGLE: ["jungle", "jg", "정글"],
            Position.MID: ["mid", "미드"],
            Position.ADC: ["adc", "ad", "원딜", "바텀", "bottom", "bot"],
            Position.SUPPORT: ["support", "sup", "서폿", "서포터"],
        }

    def _build_missing_context_message(
        self,
        message: str,
        champion_id: str | None,
        position: Position | None,
    ) -> str:
        if champion_id and position is None:
            return (
                "챔피언은 찾았지만 포지션을 찾지 못했습니다. "
                "예: `케이틀린 원딜 빌드 알려줘`, `아리 미드 룬 알려줘`처럼 "
                "포지션을 함께 질문해 주세요."
            )

        if champion_id is None and position:
            return (
                "포지션은 찾았지만 챔피언 이름을 찾지 못했습니다. "
                "예: `케이틀린 원딜 빌드 알려줘`처럼 챔피언 이름을 함께 입력해 주세요."
            )

        return (
            "챔피언 이름과 포지션을 질문 안에서 찾지 못했습니다. "
            "예: `케이틀린 원딜 빌드 알려줘`, `징크스 ADC 아이템 알려줘`, "
            "`아리 미드 카운터 알려줘`처럼 물어봐 주세요. "
            f"입력한 질문: {message}"
        )

    def _generate_answer(self, prompt: str) -> str | None:
        if self._llm_client is None:
            return None

        try:
            response = self._llm_client.models.generate_content(
                model=self._settings.gemini_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=self._settings.gemini_temperature,
                ),
            )
        except Exception:
            return None

        return response.text

    def _generate_answer_stream(self, prompt: str) -> Iterator[str]:
        if self._llm_client is None:
            return

        try:
            response_stream = self._llm_client.models.generate_content_stream(
                model=self._settings.gemini_model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=self._settings.gemini_temperature,
                ),
            )
            for response in response_stream:
                text = getattr(response, "text", None)
                if text:
                    yield text
        except Exception:
            return

    def _build_fallback_answer(
        self,
        message: str,
        build: ChampionBuildData,
        spell_names: list[str],
        start_item_names: list[str],
        core_item_names: list[str],
        counter_names: list[str],
    ) -> str:
        return (
            f"{build.champion_id} {build.position.value} 추천입니다. "
            f"룬은 {build.runes.primary_style}의 {build.runes.keystone.name}, "
            f"보조 룬은 {build.runes.secondary_style}를 추천합니다. "
            f"스펠은 {', '.join(spell_names)} 조합이 좋습니다. "
            f"시작 아이템은 {', '.join(start_item_names)}, "
            f"핵심 아이템은 {', '.join(core_item_names)} 순서로 보면 됩니다. "
            f"스킬 선마는 {' > '.join(build.skills.priority)} 입니다. "
            f"주의할 상대는 {', '.join(counter_names)} 입니다. "
            f"질문 내용: {message}"
        )

    def _build_retrieval_fallback_answer(self, retrieval: dict[str, str]) -> str:
        return (
            "Gemini 응답을 생성하지 못해 OP.GG MCP 조회 결과 원문을 기준으로 표시합니다.\n\n"
            f"**질문 유형:** {retrieval['question_type']}\n\n"
            f"**사용 도구:** `{retrieval['tool_name']}`\n\n"
            f"**조회 조건:** {retrieval['query_context']}\n\n"
            "```text\n"
            f"{self._limit_text(retrieval['retrieved_data'], 2500)}\n"
            "```"
        )

    def _build_related_champions(
        self,
        champion_ids: list[str],
    ) -> list[RelatedChampion]:
        return [
            RelatedChampion(champion_id=champion_id, name_ko=champion_id)
            for champion_id in champion_ids
        ]

    def _limit_text(self, value: str, max_length: int = 6000) -> str:
        if len(value) <= max_length:
            return value
        return value[:max_length] + "\n...(조회 데이터가 길어 일부를 생략했습니다.)"

    def _render_visual_build_summary(self, build: ChampionBuildData) -> str:
        counter_names = [counter.name_ko for counter in build.counters]
        champion_image = (
            self._render_named_image(build.champion_image, size=56)
            if build.champion_image
            else ""
        )
        sections = [
            f"### {champion_image} {build.champion_id} {build.position.value} 빌드 요약",
            self._render_rune_summary(build),
            self._render_image_row("스펠", build.spells),
            self._render_image_row("시작 아이템", build.items.start_items),
            self._render_image_row("신발", build.items.boots),
            self._render_image_row("코어 아이템", build.items.core_items),
            self._render_skill_summary(build),
        ]
        if counter_names:
            sections.append(f"**주의할 상대**\n\n{', '.join(counter_names)}")

        return "\n\n".join(section for section in sections if section)

    def _render_rune_summary(self, build: ChampionBuildData) -> str:
        keystone = self._render_named_image(build.runes.keystone)
        primary_runes = self._render_image_row_inline(
            build.runes.primary_rune_images,
            build.runes.primary_runes,
        )
        secondary_runes = self._render_image_row_inline(
            build.runes.secondary_rune_images,
            build.runes.secondary_runes,
        )
        stat_shards = ", ".join(build.runes.stat_shards)

        return (
            "**룬**\n\n"
            f"{keystone}\n\n"
            f"- 주 룬: {build.runes.primary_style} / {build.runes.keystone.name}\n"
            f"- 세부 룬: {primary_runes}\n"
            f"- 보조 룬: {build.runes.secondary_style} / {secondary_runes}\n"
            f"- 능력치 파편: {stat_shards}"
        )

    def _render_image_row(self, title: str, values: list[NamedImage]) -> str:
        if not values:
            return ""

        images = " ".join(self._render_named_image(value) for value in values)
        names = " -> ".join(value.name for value in values)
        return f"**{title}**\n\n{images}\n\n{names}"

    def _render_skill_summary(self, build: ChampionBuildData) -> str:
        if not build.skills.priority_images:
            return f"**스킬 선마**\n\n`{' > '.join(build.skills.priority)}`"

        images = " ".join(
            self._render_named_image(value)
            for value in build.skills.priority_images
        )
        names = " -> ".join(value.name for value in build.skills.priority_images)
        return f"**스킬 선마**\n\n{images}\n\n{names}"

    def _render_image_row_inline(
        self,
        values: list[NamedImage],
        fallback_names: list[str],
    ) -> str:
        if not values:
            return ", ".join(fallback_names)

        return " ".join(
            f"{self._render_named_image(value)} {value.name}"
            for value in values
        )

    def _render_named_image(self, value: NamedImage, size: int = 32) -> str:
        if value.image is None or value.image.image_url is None:
            return value.name

        alt_text = value.image.alt_text or value.name
        return (
            f'<img src="{value.image.image_url}" alt="{alt_text}" '
            f'width="{size}" height="{size}" '
            'style="vertical-align:middle;border-radius:6px;object-fit:cover;">'
        )
