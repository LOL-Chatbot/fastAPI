from app.schemas.common import Image


class ImageService:
    def get_image(self, category: str, image_key: str, alt_text: str) -> Image:
        return Image(
            image_url=f"https://example.com/{category}/{image_key}.png",
            image_key=image_key,
            alt_text=alt_text,
        )

    def get_item_image(self, item_id: int | str, alt_text: str) -> Image:
        return Image(
            image_url=f"https://ddragon.leagueoflegends.com/cdn/15.24.1/img/item/{item_id}.png",
            image_key=f"item_{item_id}",
            alt_text=alt_text,
        )

    def get_spell_image(self, spell_id: int | str, alt_text: str) -> Image:
        spell_key = self._get_spell_key(spell_id)
        return Image(
            image_url=f"https://ddragon.leagueoflegends.com/cdn/15.24.1/img/spell/{spell_key}.png",
            image_key=f"spell_{spell_id}",
            alt_text=alt_text,
        )

    def _get_spell_key(self, spell_id: int | str) -> str:
        spell_keys = {
            "4": "SummonerFlash",
            "14": "SummonerDot",
            "12": "SummonerTeleport",
            "7": "SummonerHeal",
            "6": "SummonerHaste",
            "3": "SummonerExhaust",
            "11": "SummonerSmite",
            "21": "SummonerBarrier",
            "1": "SummonerBoost",
        }
        return spell_keys.get(str(spell_id), str(spell_id))
