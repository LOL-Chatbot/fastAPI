from fastapi import HTTPException

from app.core.config import Settings, get_settings
from app.repositories.champion_repository import ChampionRepository
from app.schemas.champion import ChampionDetail, ChampionSummary, ChampionTierListItem
from app.schemas.common import Image, Position
from app.services.opgg_mcp_service import OpggMcpService


class ChampionService:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._champion_repository = ChampionRepository()
        self._opgg_mcp_service = OpggMcpService(self._settings.opgg_mcp_dir)

    def get_champions(self, position: Position | None = None) -> list[ChampionSummary]:
        champions = self._find_opgg_champions(position)
        if not champions:
            champions = self._champion_repository.find_all(position)
        return [ChampionSummary(**champion) for champion in champions]

    def get_champion_tier_list(
        self,
        position: Position | None = None,
        query: str | None = None,
    ) -> list[ChampionTierListItem]:
        positions = [position] if position is not None else list(Position)
        opgg_champions = self._get_opgg_champions_safe()
        champion_by_name = {
            champion["name_ko"]: champion
            for champion in opgg_champions
        }
        tier_items = []

        for lane_position in positions:
            try:
                meta_champions = self._opgg_mcp_service.list_lane_meta_champion_stats(
                    lane_position.value
                )
            except Exception:
                meta_champions = []

            for meta_champion in meta_champions:
                champion = champion_by_name.get(
                    meta_champion["name_ko"],
                    meta_champion,
                )
                tier_items.append(
                    ChampionTierListItem(
                        **self._to_champion_tier_item(
                            champion=champion,
                            meta_champion=meta_champion,
                            position=lane_position,
                        )
                    )
                )

        if query:
            normalized_query = self._normalize_query(query)
            tier_items = [
                item
                for item in tier_items
                if (
                    normalized_query in self._normalize_query(item.name_ko)
                    or normalized_query in self._normalize_query(item.name_en)
                    or normalized_query in item.champion_id.lower()
                )
            ]

        return sorted(
            tier_items,
            key=lambda item: (
                item.tier if item.tier > 0 else 999,
                item.rank if item.rank > 0 else 9999,
                -item.win_rate,
            ),
        )

    def get_champion(self, champion_id: str) -> ChampionDetail:
        champion = self._find_opgg_champion(champion_id)
        if champion is None:
            champion = self._champion_repository.find_by_id(champion_id)
        if champion is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": "CHAMPION_NOT_FOUND",
                    "message": "요청한 챔피언 정보를 찾을 수 없습니다.",
                },
            )

        return ChampionDetail(**champion)

    def exists_champion(self, champion_id: str) -> bool:
        return (
            self._find_opgg_champion(champion_id) is not None
            or self._champion_repository.find_by_id(champion_id) is not None
        )

    def _find_opgg_champions(self, position: Position | None = None) -> list[dict]:
        opgg_champions = self._get_opgg_champions_safe()

        if position is None:
            return [
                self._to_champion_summary(champion, [])
                for champion in opgg_champions
            ]

        try:
            meta_champions = self._opgg_mcp_service.list_lane_meta_champions(
                position.value
            )
        except Exception:
            return []

        champion_by_name = {
            champion["name_ko"]: champion
            for champion in opgg_champions
        }
        return [
            self._to_champion_summary(
                champion_by_name.get(meta_champion["name_ko"], meta_champion),
                [position],
            )
            for meta_champion in meta_champions
        ]

    def _find_opgg_champion(self, champion_id: str) -> dict | None:
        try:
            opgg_champions = self._opgg_mcp_service.list_champions()
        except Exception:
            return None

        normalized_champion_id = champion_id.lower()
        for champion in opgg_champions:
            if (
                str(champion["champion_id"]).lower() == normalized_champion_id
                or champion["key"].lower() == normalized_champion_id
                or champion["name_ko"].lower() == normalized_champion_id
            ):
                summary = self._to_champion_summary(champion, [])
                return {
                    **summary,
                    "summary": f"{summary['name_ko']} 챔피언 정보입니다.",
                }

        return None

    def _get_opgg_champions_safe(self) -> list[dict]:
        try:
            return self._opgg_mcp_service.list_champions()
        except Exception:
            return []

    def _to_champion_summary(
        self,
        champion: dict,
        positions: list[Position],
    ) -> dict:
        champion_id = str(
            champion.get("champion_id")
            or champion.get("key")
            or champion.get("name_ko", "")
        )
        champion_key = str(champion.get("key") or champion_id)
        name_ko = str(champion.get("name_ko") or champion.get("champion") or champion_id)

        return {
            "champion_id": champion_id,
            "name_ko": name_ko,
            "name_en": str(champion.get("name_en") or champion_key),
            "positions": positions,
            "image": Image(
                image_url=(
                    "https://ddragon.leagueoflegends.com/cdn/15.24.1/img/champion/"
                    f"{champion_key}.png"
                ),
                image_key=f"champion_{champion_key}",
                alt_text=name_ko,
            ),
        }

    def _to_champion_tier_item(
        self,
        champion: dict,
        meta_champion: dict,
        position: Position,
    ) -> dict:
        summary = self._to_champion_summary(champion, [position])
        return {
            **summary,
            "position": position,
            "rank": int(meta_champion.get("rank", 0)),
            "tier": int(meta_champion.get("tier", 0)),
            "win_rate": float(meta_champion.get("win_rate", 0.0)),
            "pick_rate": float(meta_champion.get("pick_rate", 0.0)),
            "ban_rate": float(meta_champion.get("ban_rate", 0.0)),
            "kda": float(meta_champion.get("kda", 0.0)),
        }

    def _normalize_query(self, value: str) -> str:
        return value.strip().lower().replace(" ", "")
