from typing import Any, NoReturn

from fastapi import HTTPException

from app.core.config import Settings, get_settings
from app.schemas.common import Position
from app.schemas.recommendation import (
    ChampionBuildData,
    CounterChampion,
    CounterRecommendationData,
    ItemBuildData,
    ItemRecommendationData,
    NamedImage,
    RuneBuildData,
    RuneRecommendationData,
    SkillBuildData,
    SkillRecommendationData,
    SpellRecommendationData,
)
from app.services.data_dragon_service import DataDragonService
from app.services.opgg_mcp_service import OpggMcpService


class RecommendationService:
    def __init__(
        self,
        settings: Settings | None = None,
        data_dragon_service: DataDragonService | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._opgg_mcp_service = OpggMcpService(self._settings.opgg_mcp_dir)
        self._data_dragon_service = data_dragon_service or DataDragonService(
            settings=self._settings
        )
        self._opgg_analysis_cache: dict[tuple[str, str], dict[str, Any]] = {}
        self._opgg_rune_analysis_cache: dict[tuple[str, str], dict[str, Any]] = {}
        self._opgg_item_analysis_cache: dict[tuple[str, str], dict[str, Any]] = {}
        self._champion_lookup_cache: dict[str, str] | None = None

    def get_champion_build(
        self,
        champion_id: str,
        position: Position,
        enemy_champion_id: str | None = None,
        play_style: str | None = None,
    ) -> ChampionBuildData:
        resolved_champion_id = self._resolve_champion_id(champion_id)
        analysis = self._get_opgg_analysis(resolved_champion_id, position)
        if analysis is None:
            self._raise_lookup_failed(resolved_champion_id, position)

        response_champion_id = self._get_response_champion_id(
            resolved_champion_id,
            analysis,
        )
        style_message = f" {play_style} 스타일을 기준으로 한" if play_style else ""
        runes = self._build_runes_from_analysis(response_champion_id, position, analysis)
        spells = self._build_spells_from_analysis(response_champion_id, position, analysis)
        items = self._build_items_from_analysis(response_champion_id, position, analysis)
        skills = self._build_skills_from_analysis(response_champion_id, position, analysis)
        counters = self._build_counters_from_analysis(
            response_champion_id,
            position,
            analysis,
        )

        return ChampionBuildData(
            champion_id=response_champion_id,
            position=position,
            champion_image=self._data_dragon_service.get_champion_image(
                response_champion_id
            ),
            runes=RuneBuildData(
                primary_style=runes.primary_style,
                keystone=runes.keystone,
                primary_runes=runes.primary_runes,
                primary_rune_images=runes.primary_rune_images,
                secondary_style=runes.secondary_style,
                secondary_runes=runes.secondary_runes,
                secondary_rune_images=runes.secondary_rune_images,
                stat_shards=runes.stat_shards,
                primary_tree=runes.primary_tree,
                secondary_tree=runes.secondary_tree,
                stat_shard_rows=runes.stat_shard_rows,
            ),
            spells=spells.spells,
            items=ItemBuildData(
                start_items=items.start_items,
                core_items=items.core_items,
                boots=items.boots,
                situational_items=items.situational_items,
            ),
            skills=SkillBuildData(
                priority=skills.priority,
                priority_images=skills.priority_images,
                description=skills.description,
            ),
            counters=counters.counters,
            summary=f"{response_champion_id}의 OP.GG MCP 기반{style_message} 추천 빌드입니다.",
        )

    def get_runes(self, champion_id: str, position: Position) -> RuneRecommendationData:
        resolved_champion_id = self._resolve_champion_id(champion_id)
        analysis = self._get_opgg_rune_analysis(resolved_champion_id, position)
        if analysis is None:
            self._raise_lookup_failed(resolved_champion_id, position)

        return self._build_runes_from_analysis(
            self._get_response_champion_id(resolved_champion_id, analysis),
            position,
            analysis,
        )

    def get_spells(self, champion_id: str, position: Position) -> SpellRecommendationData:
        resolved_champion_id = self._resolve_champion_id(champion_id)
        analysis = self._get_opgg_analysis(resolved_champion_id, position)
        if analysis is None:
            self._raise_lookup_failed(resolved_champion_id, position)

        return self._build_spells_from_analysis(
            self._get_response_champion_id(resolved_champion_id, analysis),
            position,
            analysis,
        )

    def get_items(
        self,
        champion_id: str,
        position: Position,
        enemy_champion_id: str | None = None,
    ) -> ItemRecommendationData:
        resolved_champion_id = self._resolve_champion_id(champion_id)
        analysis = self._get_opgg_item_analysis(resolved_champion_id, position)
        if analysis is None:
            self._raise_lookup_failed(resolved_champion_id, position)

        return self._build_items_from_analysis(
            self._get_response_champion_id(resolved_champion_id, analysis),
            position,
            analysis,
        )

    def get_skills(self, champion_id: str, position: Position) -> SkillRecommendationData:
        resolved_champion_id = self._resolve_champion_id(champion_id)
        analysis = self._get_opgg_analysis(resolved_champion_id, position)
        if analysis is None:
            self._raise_lookup_failed(resolved_champion_id, position)

        return self._build_skills_from_analysis(
            self._get_response_champion_id(resolved_champion_id, analysis),
            position,
            analysis,
        )

    def get_counters(
        self,
        champion_id: str,
        position: Position,
    ) -> CounterRecommendationData:
        resolved_champion_id = self._resolve_champion_id(champion_id)
        analysis = self._get_opgg_analysis(resolved_champion_id, position)
        if analysis is None:
            self._raise_lookup_failed(resolved_champion_id, position)

        return self._build_counters_from_analysis(
            self._get_response_champion_id(resolved_champion_id, analysis),
            position,
            analysis,
        )

    def resolve_champion_id(self, champion_id: str) -> str:
        return self._resolve_champion_id(champion_id)

    def find_champions_in_text(self, text: str) -> list[str]:
        mentions = self.find_champion_mentions_in_text(text)
        return [mention["champion_id"] for mention in mentions]

    def find_champion_mentions_in_text(self, text: str) -> list[dict[str, Any]]:
        normalized_text = self._normalize_lookup_key(text)
        lookup = self._get_champion_lookup()
        matches = [
            (normalized_text.find(alias), alias, key)
            for alias, key in lookup.items()
            if not alias.isdigit() and alias in normalized_text
        ]
        matches.sort(key=lambda item: (item[0], -len(item[1])))

        champion_ids = []
        seen = set()
        for index, alias, champion_id in matches:
            if champion_id in seen:
                continue
            seen.add(champion_id)
            champion_ids.append(
                {
                    "champion_id": champion_id,
                    "index": index,
                    "matched_alias": alias,
                }
            )
        return champion_ids

    def get_champion_analysis_context(
        self,
        champion_id: str,
        position: Position,
    ) -> str:
        resolved_champion_id = self._resolve_champion_id(champion_id)
        analysis = self._opgg_mcp_service.get_counter_pick_analysis(
            champion_id=resolved_champion_id,
            position=position.value,
        )
        return self._format_counter_pick_context(
            champion_id=resolved_champion_id,
            position=position,
            analysis=analysis,
        )

    def get_opgg_champion_analysis_raw(
        self,
        champion_id: str,
        position: Position,
    ) -> str:
        return self._opgg_mcp_service.get_champion_analysis_raw(
            champion_id=self._resolve_champion_id(champion_id),
            position=position.value,
        )

    def get_opgg_champion_synergies_raw(
        self,
        champion_id: str,
        my_position: Position,
        synergy_position: Position,
    ) -> str:
        return self._opgg_mcp_service.get_champion_synergies(
            champion_id=self._resolve_champion_id(champion_id),
            my_position=my_position.value,
            synergy_position=synergy_position.value,
        )

    def get_opgg_lane_matchup_guide_raw(
        self,
        my_champion_id: str,
        opponent_champion_id: str,
        position: Position,
    ) -> str:
        return self._opgg_mcp_service.get_lane_matchup_guide(
            my_champion_id=self._resolve_champion_id(my_champion_id),
            opponent_champion_id=self._resolve_champion_id(opponent_champion_id),
            position=position.value,
        )

    def get_opgg_champion_details_raw(self, champion_ids: list[str]) -> str:
        return self._opgg_mcp_service.list_champion_details(
            [self._resolve_champion_id(champion_id) for champion_id in champion_ids]
        )

    def get_opgg_champion_leaderboard_raw(
        self,
        champion_id: str,
        region: str = "KR",
    ) -> str:
        return self._opgg_mcp_service.list_champion_leaderboard(
            champion_id=self._resolve_champion_id(champion_id),
            region=region,
        )

    def get_opgg_champions_raw(self) -> str:
        return self._opgg_mcp_service.list_champions_raw()

    def get_opgg_lane_meta_raw(self, position: Position) -> str:
        return self._opgg_mcp_service.list_lane_meta_champions_raw(position.value)

    def get_lane_meta_context(self, position: Position) -> str:
        return self._opgg_mcp_service.list_lane_meta_champions_raw(position.value)

    def get_champion_synergy_context(
        self,
        champion_id: str,
        my_position: Position,
        synergy_position: Position | None = None,
    ) -> str:
        resolved_champion_id = self._resolve_champion_id(champion_id)
        resolved_synergy_position = synergy_position or Position.SUPPORT
        analysis = self._opgg_mcp_service.get_champion_synergies_analysis(
            champion_id=resolved_champion_id,
            my_position=my_position.value,
            synergy_position=resolved_synergy_position.value,
        )
        return self._format_synergy_context(
            champion_id=resolved_champion_id,
            my_position=my_position,
            synergy_position=resolved_synergy_position,
            analysis=analysis,
        )

    def get_lane_matchup_context(
        self,
        my_champion_id: str,
        opponent_champion_id: str,
        position: Position,
    ) -> str:
        return self._opgg_mcp_service.get_lane_matchup_guide(
            my_champion_id=self._resolve_champion_id(my_champion_id),
            opponent_champion_id=self._resolve_champion_id(opponent_champion_id),
            position=position.value,
        )

    def get_champion_detail_context(self, champion_ids: list[str]) -> str:
        resolved_champion_ids = [
            self._resolve_champion_id(champion_id)
            for champion_id in champion_ids
        ]
        return self._opgg_mcp_service.list_champion_details(resolved_champion_ids)

    def get_champion_leaderboard_context(
        self,
        champion_id: str,
        region: str = "KR",
    ) -> str:
        return self._opgg_mcp_service.list_champion_leaderboard(
            champion_id=self._resolve_champion_id(champion_id),
            region=region,
        )

    def check_opgg_mcp(self) -> dict[str, Any]:
        try:
            champions = self._opgg_mcp_service.list_champions()
        except Exception as exc:
            return {
                "status": "error",
                "ok": False,
                "message": "OP.GG MCP 응답 확인에 실패했습니다.",
                "detail": str(exc),
            }

        return {
            "status": "ok",
            "ok": True,
            "message": "OP.GG MCP 응답이 정상입니다.",
            "champion_count": len(champions),
        }

    def _get_opgg_analysis(
        self,
        champion_id: str,
        position: Position,
    ) -> dict[str, Any] | None:
        cache_key = (champion_id.upper(), position.value.upper())
        if cache_key in self._opgg_analysis_cache:
            return self._opgg_analysis_cache[cache_key]

        try:
            analysis = self._opgg_mcp_service.get_champion_analysis(
                champion_id=champion_id,
                position=position.value,
            )
        except Exception:
            return None

        self._opgg_analysis_cache[cache_key] = analysis
        return analysis

    def _get_opgg_rune_analysis(
        self,
        champion_id: str,
        position: Position,
    ) -> dict[str, Any] | None:
        cache_key = (champion_id.upper(), position.value.upper())
        if cache_key in self._opgg_analysis_cache:
            return self._opgg_analysis_cache[cache_key]

        if cache_key in self._opgg_rune_analysis_cache:
            return self._opgg_rune_analysis_cache[cache_key]

        try:
            analysis = self._opgg_mcp_service.get_rune_analysis(
                champion_id=champion_id,
                position=position.value,
            )
        except Exception:
            return None

        self._opgg_rune_analysis_cache[cache_key] = analysis
        return analysis

    def _get_opgg_item_analysis(
        self,
        champion_id: str,
        position: Position,
    ) -> dict[str, Any] | None:
        cache_key = (champion_id.upper(), position.value.upper())
        if cache_key in self._opgg_analysis_cache:
            return self._opgg_analysis_cache[cache_key]

        if cache_key in self._opgg_item_analysis_cache:
            return self._opgg_item_analysis_cache[cache_key]

        try:
            analysis = self._opgg_mcp_service.get_item_analysis(
                champion_id=champion_id,
                position=position.value,
            )
        except Exception:
            return None

        self._opgg_item_analysis_cache[cache_key] = analysis
        return analysis

    def _build_runes_from_analysis(
        self,
        champion_id: str,
        position: Position,
        analysis: dict[str, Any],
    ) -> RuneRecommendationData:
        runes = analysis.get("runes", {})
        primary_runes = runes.get("primary_rune_names", [])
        secondary_runes = runes.get("secondary_rune_names", [])
        stat_mod_names = runes.get("stat_mod_names", [])
        keystone_name = primary_runes[0] if primary_runes else ""
        keystone = self._data_dragon_service.get_rune(keystone_name)
        primary_rune_images = [
            self._data_dragon_service.get_rune(rune_name)
            for rune_name in primary_runes[1:]
        ]
        secondary_rune_images = [
            self._data_dragon_service.get_rune(rune_name)
            for rune_name in secondary_runes
        ]

        return RuneRecommendationData(
            champion_id=champion_id,
            position=position,
            primary_style=self._data_dragon_service.get_rune_style_name(
                runes.get("primary_page_name", "")
            ),
            keystone=keystone,
            primary_runes=[rune.name for rune in primary_rune_images],
            primary_rune_images=primary_rune_images,
            secondary_style=self._data_dragon_service.get_rune_style_name(
                runes.get("secondary_page_name", "")
            ),
            secondary_runes=[rune.name for rune in secondary_rune_images],
            secondary_rune_images=secondary_rune_images,
            stat_shards=[
                self._data_dragon_service.get_stat_shard_name(value)
                for value in stat_mod_names
            ],
            primary_tree=self._data_dragon_service.get_rune_tree(
                style_name=str(runes.get("primary_page_name", "")),
                selected_rune_names=primary_runes,
            ),
            secondary_tree=self._data_dragon_service.get_rune_tree(
                style_name=str(runes.get("secondary_page_name", "")),
                selected_rune_names=secondary_runes,
            ),
            stat_shard_rows=self._data_dragon_service.get_stat_shard_rows(stat_mod_names),
        )

    def _build_spells_from_analysis(
        self,
        champion_id: str,
        position: Position,
        analysis: dict[str, Any],
    ) -> SpellRecommendationData:
        spell_data = analysis.get("summoner_spells", {})
        spell_ids = spell_data.get("ids", [])

        return SpellRecommendationData(
            champion_id=champion_id,
            position=position,
            spells=[
                self._data_dragon_service.get_summoner_spell(spell_id)
                for spell_id in spell_ids
            ],
        )

    def _build_items_from_analysis(
        self,
        champion_id: str,
        position: Position,
        analysis: dict[str, Any],
    ) -> ItemRecommendationData:
        return ItemRecommendationData(
            champion_id=champion_id,
            position=position,
            start_items=self._named_items(analysis.get("starter_items", {})),
            core_items=self._named_items(analysis.get("core_items", {})),
            boots=self._named_items(analysis.get("boots", {})),
            situational_items=[],
        )

    def _build_skills_from_analysis(
        self,
        champion_id: str,
        position: Position,
        analysis: dict[str, Any],
    ) -> SkillRecommendationData:
        skill_masteries = analysis.get("skill_masteries", {})
        priority = skill_masteries.get("ids", [])
        skill_order = analysis.get("skills", {}).get("order", [])
        priority_images = [
            self._data_dragon_service.get_champion_skill(champion_id, skill_key)
            for skill_key in priority
        ]

        return SkillRecommendationData(
            champion_id=champion_id,
            position=position,
            priority=priority,
            priority_images=priority_images,
            description=(
                f"스킬 선마는 {' > '.join(priority)} 순서를 추천합니다. "
                f"레벨별 추천 순서는 {' - '.join(skill_order)} 입니다."
            ),
        )

    def _build_counters_from_analysis(
        self,
        champion_id: str,
        position: Position,
        analysis: dict[str, Any],
    ) -> CounterRecommendationData:
        counters = [
            CounterChampion(
                champion_id=str(counter.get("champion_id", "")),
                name_ko=str(counter.get("champion_name", "")),
                reason=(
                    "OP.GG 기준 상대 승률 "
                    f"{counter.get('win_rate', 0):.0%}인 까다로운 매치업입니다."
                ),
                image=self._data_dragon_service.get_champion_image(
                    str(counter.get("champion_id", ""))
                ).image,
            )
            for counter in analysis.get("strong_counters", [])
        ]

        return CounterRecommendationData(
            champion_id=champion_id,
            position=position,
            counters=counters,
        )

    def _format_counter_pick_context(
        self,
        champion_id: str,
        position: Position,
        analysis: dict[str, Any],
    ) -> str:
        difficult_matchups = analysis.get("strong_counters", [])
        easy_matchups = analysis.get("weak_counters", [])
        return "\n".join(
            [
                "[카운터 해석 기준]",
                f"- 분석 대상: {champion_id} {position.value}",
                "- win_rate는 분석 대상 챔피언의 해당 상대전 승률입니다.",
                "- 카운터는 분석 대상 챔피언의 win_rate가 낮은 상대입니다.",
                "- win_rate가 높은 상대는 카운터가 아니라 상대하기 쉬운 챔피언입니다.",
                "- 답변에서 카운터를 말할 때는 반드시 아래 카운터 후보 목록만 사용합니다.",
                "",
                "[카운터 후보: 분석 대상 챔피언 승률 낮은 순]",
                self._format_matchup_rows(difficult_matchups),
                "",
                "[상대하기 쉬운 후보: 답변에서 카운터로 추천 금지]",
                self._format_matchup_rows(easy_matchups),
            ]
        )

        return "\n".join(
            [
                "[카운터 해석 기준]",
                f"- 분석 대상: {champion_id} {position.value}",
                "- win_rate는 분석 대상 챔피언의 해당 상대전 승률입니다.",
                "- 카운터는 분석 대상 챔피언의 win_rate가 낮은 상대입니다.",
                "- win_rate가 높은 상대는 카운터가 아니라 상대하기 쉬운 챔피언입니다.",
                "",
                "[카운터 후보: 분석 대상 챔피언 승률 낮은 순]",
                self._format_matchup_rows(difficult_matchups),
                "",
                "[상대하기 쉬운 후보: 분석 대상 챔피언 승률 높은 순]",
                self._format_matchup_rows(easy_matchups),
                "",
                "[OP.GG MCP 원문]",
                str(analysis.get("raw_text", "")),
            ]
        )

    def _format_matchup_rows(self, matchups: list[dict[str, Any]]) -> str:
        if not matchups:
            return "- 조회된 매치업 데이터가 없습니다."

        return "\n".join(
            (
                "- {name}: 기준 챔피언 승률 {win_rate:.0%}, "
                "표본 {play}게임, 승리 {win}게임"
            ).format(
                name=matchup.get("champion_name", ""),
                win_rate=matchup.get("win_rate", 0),
                play=matchup.get("play", 0),
                win=matchup.get("win", 0),
            )
            for matchup in matchups
        )

    def _format_synergy_context(
        self,
        champion_id: str,
        my_position: Position,
        synergy_position: Position,
        analysis: dict[str, Any],
    ) -> str:
        synergies = analysis.get("synergies", [])
        return "\n".join(
            [
                "[시너지 추천 기준]",
                f"- 기준 챔피언: {champion_id} {my_position.value}",
                f"- 추천 대상 포지션: {synergy_position.value}",
                "- OP.GG MCP 응답에는 별도 pick_rate 필드가 없으므로 play를 조합 표본/픽 지표로 사용합니다.",
                "- 추천 순서는 조합 승률 win_rate를 우선하고, 조회 후보 내 선택 비중(play_share)을 보조 지표로 반영합니다.",
                "- synergy_tier_data는 OP.GG MCP가 함께 반환한 시너지 챔피언의 포지션 티어/랭크 데이터입니다.",
                "",
                "[추천 후보: 승률 + 조합 표본 비중 종합 순]",
                self._format_synergy_rows(synergies[:8]),
            ]
        )

    def _format_synergy_rows(self, synergies: list[dict[str, Any]]) -> str:
        if not synergies:
            return "- 조회된 시너지 데이터가 없습니다."

        return "\n".join(
            (
                "- {name}: 조합 승률 {win_rate:.0%}, 조합 표본 {play}게임, "
                "후보 내 선택 비중 {play_share:.1%}, OP.GG 시너지 순위 {score_rank}위, "
                "포지션 티어 {tier}티어/{rank}위"
            ).format(
                name=synergy.get("synergy_champion_name", ""),
                win_rate=synergy.get("win_rate", 0),
                play=synergy.get("play", 0),
                play_share=synergy.get("play_share", 0),
                score_rank=synergy.get("score_rank", 0),
                tier=synergy.get("synergy_tier", 0),
                rank=synergy.get("synergy_tier_rank", 0),
            )
            for synergy in synergies
        )

    def _named_items(self, item_data: dict[str, Any]) -> list[NamedImage]:
        item_ids = item_data.get("ids", [])
        item_names = item_data.get("ids_names", [])

        return [
            self._data_dragon_service.get_item(item_id, str(item_name))
            for item_id, item_name in zip(item_ids, item_names)
        ]

    def find_champion_in_text(self, text: str) -> str | None:
        normalized_text = self._normalize_lookup_key(text)
        lookup = self._get_champion_lookup()
        matches = [
            (alias, key)
            for alias, key in lookup.items()
            if not alias.isdigit() and alias in normalized_text
        ]
        if not matches:
            return None

        matches.sort(key=lambda item: len(item[0]), reverse=True)
        return matches[0][1]

    def _resolve_champion_id(self, champion_id: str) -> str:
        normalized_input = self._normalize_lookup_key(champion_id)
        lookup = self._get_champion_lookup()
        return lookup.get(normalized_input, champion_id.strip())

    def _get_champion_lookup(self) -> dict[str, str]:
        if self._champion_lookup_cache is not None:
            return self._champion_lookup_cache

        lookup: dict[str, str] = {}
        try:
            champions = self._opgg_mcp_service.list_champions()
        except Exception:
            self._champion_lookup_cache = lookup
            return lookup

        for champion in champions:
            key = str(champion.get("key", "")).strip()
            if not key:
                continue

            for value in (
                champion.get("champion_id"),
                champion.get("key"),
                champion.get("name_ko"),
                champion.get("name_en"),
            ):
                if value:
                    lookup[self._normalize_lookup_key(str(value))] = key

        self._champion_lookup_cache = lookup
        return lookup

    def _normalize_lookup_key(self, value: str) -> str:
        return (
            value.strip()
            .lower()
            .replace(" ", "")
            .replace("'", "")
            .replace(".", "")
        )

    def _get_response_champion_id(
        self,
        champion_id: str,
        analysis: dict[str, Any],
    ) -> str:
        return str(analysis.get("champion") or champion_id)

    def _raise_lookup_failed(self, champion_id: str, position: Position) -> NoReturn:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "RECOMMENDATION_NOT_FOUND",
                "message": (
                    f"{champion_id} {position.value} 정보 조회 실패: "
                    "OP.GG 추천 정보를 가져오지 못했습니다."
                ),
            },
        )
