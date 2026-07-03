import json
from typing import Any
from urllib.request import urlopen

from app.core.config import Settings, get_settings
from app.schemas.common import Image
from app.schemas.recommendation import NamedImage


class DataDragonService:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._version: str | None = self._settings.data_dragon_version
        self._ko_runes: list[dict[str, Any]] | None = None
        self._en_runes: list[dict[str, Any]] | None = None
        self._ko_summoner: dict[str, Any] | None = None
        self._ko_items: dict[str, Any] | None = None
        self._ko_champions: dict[str, Any] | None = None
        self._ko_champion_details: dict[str, dict[str, Any]] = {}
        self._rune_by_en_name: dict[str, NamedImage] | None = None
        self._style_by_en_name: dict[str, str] | None = None

    @property
    def version(self) -> str:
        if self._version is None:
            versions = self._fetch_json(
                "https://ddragon.leagueoflegends.com/api/versions.json"
            )
            self._version = versions[0]

        return self._version

    def get_rune_style_name(self, style_name: str) -> str:
        style_by_en_name = self._get_style_by_en_name()
        return style_by_en_name.get(style_name, style_name)

    def get_rune(self, rune_name: str) -> NamedImage:
        rune_by_en_name = self._get_rune_by_en_name()
        return rune_by_en_name.get(rune_name, NamedImage(name=rune_name))

    def get_stat_shard_name(self, stat_shard_id: int | str) -> str:
        stat_shards = {
            "5001": "체력 증가",
            "5002": "방어력",
            "5003": "마법 저항력",
            "5005": "공격 속도",
            "5007": "스킬 가속",
            "5008": "적응형 능력치",
            "5011": "체력 증가",
        }
        return stat_shards.get(str(stat_shard_id), str(stat_shard_id))

    def get_summoner_spell(self, spell_id: int | str) -> NamedImage:
        spells = self._get_ko_summoner().get("data", {})
        spell_key = str(spell_id)

        for spell in spells.values():
            if str(spell.get("key")) == spell_key:
                image_full = spell.get("image", {}).get("full")
                name = spell.get("name", spell_key)
                return NamedImage(
                    name=name,
                    image=Image(
                        image_url=self._versioned_asset_url("spell", image_full),
                        image_key=f"spell_{spell_key}",
                        alt_text=name,
                    ),
                )

        return NamedImage(name=spell_key)

    def get_item(self, item_id: int | str, fallback_name: str | None = None) -> NamedImage:
        item_key = str(item_id)
        item = self._get_ko_items().get("data", {}).get(item_key)

        if item is None:
            return NamedImage(name=fallback_name or item_key)

        image_full = item.get("image", {}).get("full")
        name = item.get("name", fallback_name or item_key)
        return NamedImage(
            name=name,
            image=Image(
                image_url=self._versioned_asset_url("item", image_full),
                image_key=f"item_{item_key}",
                alt_text=name,
            ),
        )

    def get_champion_image(self, champion_id: str) -> NamedImage:
        champion = self._find_champion(champion_id)
        if champion is None:
            return NamedImage(name=champion_id)

        image_full = champion.get("image", {}).get("full")
        name = champion.get("name", champion.get("id", champion_id))
        return NamedImage(
            name=name,
            image=Image(
                image_url=self._versioned_asset_url("champion", image_full),
                image_key=f"champion_{champion.get('id', champion_id)}",
                alt_text=name,
            ),
        )

    def get_champion_skill(self, champion_id: str, skill_key: str) -> NamedImage:
        champion = self._find_champion(champion_id)
        if champion is None:
            return NamedImage(name=skill_key)

        detail = self._get_ko_champion_detail(str(champion.get("id", champion_id)))
        skill_index = {"Q": 0, "W": 1, "E": 2, "R": 3}.get(skill_key.upper())
        spells = detail.get("spells", [])
        if skill_index is None or skill_index >= len(spells):
            return NamedImage(name=skill_key)

        spell = spells[skill_index]
        image_full = spell.get("image", {}).get("full")
        name = spell.get("name", skill_key.upper())
        return NamedImage(
            name=f"{skill_key.upper()} {name}",
            image=Image(
                image_url=self._versioned_asset_url("spell", image_full),
                image_key=f"skill_{champion.get('id', champion_id)}_{skill_key.upper()}",
                alt_text=name,
            ),
        )

    def _get_rune_by_en_name(self) -> dict[str, NamedImage]:
        if self._rune_by_en_name is not None:
            return self._rune_by_en_name

        rune_by_id = self._build_rune_by_id()
        self._rune_by_en_name = {}

        for style in self._get_en_runes():
            for slot in style.get("slots", []):
                for rune in slot.get("runes", []):
                    rune_id = rune.get("id")
                    ko_rune = rune_by_id.get(rune_id)
                    if ko_rune is None:
                        continue

                    name = ko_rune.get("name", rune.get("name", ""))
                    icon = ko_rune.get("icon")
                    self._rune_by_en_name[rune.get("name", "")] = NamedImage(
                        name=name,
                        image=Image(
                            image_url=self._global_asset_url(icon),
                            image_key=f"rune_{rune_id}",
                            alt_text=name,
                        ),
                    )

        return self._rune_by_en_name

    def _get_style_by_en_name(self) -> dict[str, str]:
        if self._style_by_en_name is not None:
            return self._style_by_en_name

        ko_style_by_id = {
            style.get("id"): style.get("name", "")
            for style in self._get_ko_runes()
        }
        self._style_by_en_name = {
            style.get("name", ""): ko_style_by_id.get(style.get("id"), style.get("name", ""))
            for style in self._get_en_runes()
        }
        return self._style_by_en_name

    def _build_rune_by_id(self) -> dict[int, dict[str, Any]]:
        rune_by_id = {}
        for style in self._get_ko_runes():
            for slot in style.get("slots", []):
                for rune in slot.get("runes", []):
                    rune_by_id[rune.get("id")] = rune
        return rune_by_id

    def _get_ko_runes(self) -> list[dict[str, Any]]:
        if self._ko_runes is None:
            self._ko_runes = self._fetch_json(
                self._data_url(self._settings.data_dragon_language, "runesReforged.json")
            )
        return self._ko_runes

    def _get_en_runes(self) -> list[dict[str, Any]]:
        if self._en_runes is None:
            self._en_runes = self._fetch_json(
                self._data_url("en_US", "runesReforged.json")
            )
        return self._en_runes

    def _get_ko_summoner(self) -> dict[str, Any]:
        if self._ko_summoner is None:
            self._ko_summoner = self._fetch_json(
                self._data_url(self._settings.data_dragon_language, "summoner.json")
            )
        return self._ko_summoner

    def _get_ko_items(self) -> dict[str, Any]:
        if self._ko_items is None:
            self._ko_items = self._fetch_json(
                self._data_url(self._settings.data_dragon_language, "item.json")
            )
        return self._ko_items

    def _get_ko_champions(self) -> dict[str, Any]:
        if self._ko_champions is None:
            self._ko_champions = self._fetch_json(
                self._data_url(self._settings.data_dragon_language, "champion.json")
            )
        return self._ko_champions

    def _get_ko_champion_detail(self, champion_id: str) -> dict[str, Any]:
        if champion_id not in self._ko_champion_details:
            detail = self._fetch_json(
                self._data_url(
                    self._settings.data_dragon_language,
                    f"champion/{champion_id}.json",
                )
            )
            self._ko_champion_details[champion_id] = detail.get("data", {}).get(
                champion_id,
                {},
            )
        return self._ko_champion_details[champion_id]

    def _find_champion(self, champion_id: str) -> dict[str, Any] | None:
        normalized_champion_id = self._normalize_champion_key(champion_id)
        for champion in self._get_ko_champions().get("data", {}).values():
            aliases = [
                champion.get("id", ""),
                champion.get("key", ""),
                champion.get("name", ""),
            ]
            if normalized_champion_id in {
                self._normalize_champion_key(str(alias))
                for alias in aliases
                if alias
            }:
                return champion
        return None

    def _normalize_champion_key(self, value: str) -> str:
        return value.strip().lower().replace(" ", "").replace("'", "").replace(".", "")

    def _data_url(self, language: str, file_name: str) -> str:
        return (
            "https://ddragon.leagueoflegends.com/cdn/"
            f"{self.version}/data/{language}/{file_name}"
        )

    def _versioned_asset_url(self, category: str, image_full: str | None) -> str | None:
        if not image_full:
            return None

        return (
            "https://ddragon.leagueoflegends.com/cdn/"
            f"{self.version}/img/{category}/{image_full}"
        )

    def _global_asset_url(self, icon: str | None) -> str | None:
        if not icon:
            return None

        return f"https://ddragon.leagueoflegends.com/cdn/img/{icon}"

    def _fetch_json(self, url: str) -> Any:
        with urlopen(url, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
