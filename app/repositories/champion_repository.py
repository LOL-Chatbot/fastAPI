from app.schemas.common import Image, Position


class ChampionRepository:
    def __init__(self) -> None:
        self._champions = {
            "garen": {
                "champion_id": "garen",
                "name_ko": "가렌",
                "name_en": "Garen",
                "positions": [Position.TOP],
                "summary": "단순하고 튼튼한 전사형 챔피언입니다.",
                "image": Image(
                    image_url="https://example.com/champions/garen.png",
                    image_key="champion_garen",
                    alt_text="가렌",
                ),
            },
            "darius": {
                "champion_id": "darius",
                "name_ko": "다리우스",
                "name_en": "Darius",
                "positions": [Position.TOP],
                "summary": "근접 교전과 출혈 누적에 강한 탑 챔피언입니다.",
                "image": Image(
                    image_url="https://example.com/champions/darius.png",
                    image_key="champion_darius",
                    alt_text="다리우스",
                ),
            },
        }

    def find_all(self, position: Position | None = None) -> list[dict]:
        champions = list(self._champions.values())
        if position is None:
            return champions

        return [
            champion
            for champion in champions
            if position in champion["positions"]
        ]

    def find_by_id(self, champion_id: str) -> dict | None:
        return self._champions.get(champion_id.lower())
