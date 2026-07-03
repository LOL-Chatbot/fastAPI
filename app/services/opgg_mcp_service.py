import ast
import json
import re
import subprocess
from pathlib import Path
from typing import Any


class OpggMcpService:
    CHAMPION_LIST_OUTPUT_FIELDS = [
        "data.champions[].{champion_id,key,name}",
    ]

    LANE_META_OUTPUT_FIELDS = [
        "data.positions.{position}[].champion",
    ]

    LANE_META_CHAT_OUTPUT_FIELDS = [
        "data.positions.{position}[].{champion,win_rate,pick_rate,ban_rate,tier,rank,kda,play,role_rate}",
    ]

    COUNTER_PICK_OUTPUT_FIELDS = [
        "champion",
        "position",
        "data.summary.average_stats.{win_rate,pick_rate,ban_rate,kda,play,tier,rank}",
        "data.strong_counters[].{champion_id,champion_name,play,win,win_rate}",
        "data.weak_counters[].{champion_id,champion_name,play,win,win_rate}",
    ]

    SYNERGY_OUTPUT_FIELDS = [
        "champion",
        "my_position",
        "synergy_position",
        "data.synergies[].{champion_id,champion_name,play,position,score,score_rank,synergy_champion_id,synergy_champion_name,synergy_position,win,win_rate}",
        "data.synergies[].synergy_tier_data.{rank,tier}",
    ]

    CHAMPION_DETAIL_OUTPUT_FIELDS = [
        "requested_champions[]",
        "data.champions[].{id,key,name,title,blurb,lore,tags[],ally_tips[],enemy_tips[],partype}",
        "data.champions[].info.{attack,defense,difficulty,magic}",
        "data.champions[].passive.{name,description}",
        "data.champions[].spells[].{key,name,description,cooldown_burn[],cost_burn[],range_burn[]}",
        "data.champions[].stats.{hp,mp,armor,spellblock,attackdamage,attackrange,movespeed}",
    ]

    CHAMPION_LEADERBOARD_OUTPUT_FIELDS = [
        "region",
        "champion",
        "leaderboard[].rank",
        "leaderboard[].summoner.{game_name,name,tagline,level,profile_image_url}",
        "leaderboard[].summoner.league_stats[].tier_info.{tier,division,lp}",
        "leaderboard[].most_champion_stat.{play,win,lose,kill,death,assist,op_score,gold_earned,minion_kill,damage_dealt_to_champions}",
    ]

    RUNE_OUTPUT_FIELDS = [
        "champion",
        "position",
        "data.runes.{primary_page_name,primary_rune_names[],secondary_page_name,secondary_rune_names[],stat_mod_names[],pick_rate,play,win}",
    ]

    ITEM_OUTPUT_FIELDS = [
        "champion",
        "position",
        "data.starter_items.{ids,ids_names,play,win,pick_rate}",
        "data.boots.{ids,ids_names,play,win,pick_rate}",
        "data.core_items.{ids,ids_names,play,win,pick_rate}",
    ]

    CHAMPION_ANALYSIS_OUTPUT_FIELDS = [
        "champion",
        "position",
        "data.summary.average_stats.{win_rate,pick_rate,ban_rate,kda,play,tier,rank}",
        "data.{damage_type,mythic_items}",
        "data.runes.{primary_page_name,primary_rune_names[],secondary_page_name,secondary_rune_names[],stat_mod_names[],pick_rate,play,win}",
        "data.summoner_spells.{ids,ids_names,play,win,pick_rate}",
        "data.starter_items.{ids,ids_names,play,win,pick_rate}",
        "data.boots.{ids,ids_names,play,win,pick_rate}",
        "data.core_items.{ids,ids_names,play,win,pick_rate}",
        "data.fourth_items[].{ids,ids_names,play,win,pick_rate}",
        "data.fifth_items[].{ids,ids_names,play,win,pick_rate}",
        "data.sixth_items[].{ids,ids_names,play,win,pick_rate}",
        "data.skill_masteries.{ids,play,win,pick_rate}",
        "data.skills.{order,play,win,pick_rate}",
        "data.skill_combos[].{name,video_url}",
        "data.strong_counters[].{champion_id,champion_name,play,win,win_rate}",
        "data.weak_counters[].{champion_id,champion_name,play,win,win_rate}",
        "data.synergies.adc[].{champion_id,champion_name,play,position,score,score_rank,synergy_champion_id,synergy_champion_name,synergy_position,win,win_rate}",
        "data.synergies.jungle[].{champion_id,champion_name,play,position,score,score_rank,synergy_champion_id,synergy_champion_name,synergy_position,win,win_rate}",
        "data.synergies.mid[].{champion_id,champion_name,play,position,score,score_rank,synergy_champion_id,synergy_champion_name,synergy_position,win,win_rate}",
        "data.synergies.support[].{champion_id,champion_name,play,position,score,score_rank,synergy_champion_id,synergy_champion_name,synergy_position,win,win_rate}",
    ]

    def __init__(self, mcp_dir: str) -> None:
        self._mcp_dir = Path(mcp_dir)
        self._node_command = ["node", "dist/index.js"]
        self._response_cache: dict[str, str] = {}

    def get_champion_analysis(
        self,
        champion_id: str,
        position: str,
    ) -> dict[str, Any]:
        result = self.get_champion_analysis_raw(champion_id, position)
        return self._parse_champion_analysis(result)

    def get_champion_analysis_raw(
        self,
        champion_id: str,
        position: str,
    ) -> str:
        return self._call_tool(
            tool_name="lol_get_champion_analysis",
            arguments={
                "champion": champion_id.upper(),
                "position": position.lower(),
                "game_mode": "ranked",
                "lang": "ko_KR",
                "desired_output_fields": self.CHAMPION_ANALYSIS_OUTPUT_FIELDS,
            },
        )

    def get_rune_analysis(
        self,
        champion_id: str,
        position: str,
    ) -> dict[str, Any]:
        result = self._call_tool(
            tool_name="lol_get_champion_analysis",
            arguments={
                "champion": champion_id.upper(),
                "position": position.upper(),
                "game_mode": "RANKED",
                "desired_output_fields": self.RUNE_OUTPUT_FIELDS,
            },
        )
        return self._parse_champion_analysis(result)

    def get_item_analysis(
        self,
        champion_id: str,
        position: str,
    ) -> dict[str, Any]:
        result = self._call_tool(
            tool_name="lol_get_champion_analysis",
            arguments={
                "champion": champion_id.upper(),
                "position": position.upper(),
                "game_mode": "RANKED",
                "desired_output_fields": self.ITEM_OUTPUT_FIELDS,
            },
        )
        return self._parse_item_analysis(result)

    def list_champions(self) -> list[dict[str, Any]]:
        result = self.list_champions_raw()
        return self._parse_champions(result)

    def list_champions_raw(self) -> str:
        return self._call_tool(
            tool_name="lol_list_champions",
            arguments={
                "lang": "ko_KR",
                "desired_output_fields": self.CHAMPION_LIST_OUTPUT_FIELDS,
            },
        )

    def list_lane_meta_champions(self, position: str) -> list[dict[str, Any]]:
        normalized_position = position.lower()
        result = self._call_tool(
            tool_name="lol_list_lane_meta_champions",
            arguments={
                "lang": "ko_KR",
                "position": normalized_position,
                "desired_output_fields": [
                    field.replace("{position}", normalized_position)
                    for field in self.LANE_META_OUTPUT_FIELDS
                ],
            },
        )
        return self._parse_lane_meta_champions(result, normalized_position)

    def list_lane_meta_champion_stats(self, position: str) -> list[dict[str, Any]]:
        normalized_position = position.lower()
        result = self._call_tool(
            tool_name="lol_list_lane_meta_champions",
            arguments={
                "lang": "ko_KR",
                "position": normalized_position,
                "desired_output_fields": [
                    field.replace("{position}", normalized_position)
                    for field in self.LANE_META_CHAT_OUTPUT_FIELDS
                ],
            },
        )
        return self._parse_lane_meta_champions(result, normalized_position)

    def get_counter_pick_data(self, champion_id: str, position: str) -> str:
        return self._call_tool(
            tool_name="lol_get_champion_analysis",
            arguments={
                "champion": champion_id.upper(),
                "position": position.lower(),
                "game_mode": "ranked",
                "lang": "ko_KR",
                "desired_output_fields": self.COUNTER_PICK_OUTPUT_FIELDS,
            },
        )

    def get_counter_pick_analysis(
        self,
        champion_id: str,
        position: str,
    ) -> dict[str, Any]:
        result = self.get_counter_pick_data(champion_id, position)
        return self._parse_champion_analysis(result)

    def list_lane_meta_champions_raw(self, position: str) -> str:
        normalized_position = position.lower()
        return self._call_tool(
            tool_name="lol_list_lane_meta_champions",
            arguments={
                "lang": "ko_KR",
                "position": normalized_position,
                "desired_output_fields": [
                    field.replace("{position}", normalized_position)
                    for field in self.LANE_META_CHAT_OUTPUT_FIELDS
                ],
            },
        )

    def get_champion_synergies(
        self,
        champion_id: str,
        my_position: str,
        synergy_position: str,
    ) -> str:
        return self._call_tool(
            tool_name="lol_get_champion_synergies",
            arguments={
                "champion": champion_id.upper(),
                "my_position": my_position.lower(),
                "synergy_position": synergy_position.lower(),
                "lang": "ko_KR",
                "desired_output_fields": self.SYNERGY_OUTPUT_FIELDS,
            },
        )

    def get_champion_synergies_analysis(
        self,
        champion_id: str,
        my_position: str,
        synergy_position: str,
    ) -> dict[str, Any]:
        result = self.get_champion_synergies(
            champion_id=champion_id,
            my_position=my_position,
            synergy_position=synergy_position,
        )
        return self._parse_champion_synergies(result)

    def get_lane_matchup_guide(
        self,
        my_champion_id: str,
        opponent_champion_id: str,
        position: str,
    ) -> str:
        return self._call_tool(
            tool_name="lol_get_lane_matchup_guide",
            arguments={
                "my_champion": my_champion_id.upper(),
                "opponent_champion": opponent_champion_id.upper(),
                "position": position.lower(),
                "lang": "ko_KR",
            },
        )

    def list_champion_details(self, champion_ids: list[str]) -> str:
        return self._call_tool(
            tool_name="lol_list_champion_details",
            arguments={
                "lang": "ko_KR",
                "champions": [champion_id.upper() for champion_id in champion_ids[:10]],
                "desired_output_fields": self.CHAMPION_DETAIL_OUTPUT_FIELDS,
            },
        )

    def list_champion_leaderboard(
        self,
        champion_id: str,
        region: str = "KR",
    ) -> str:
        return self._call_tool(
            tool_name="lol_list_champion_leaderboard",
            arguments={
                "region": region.upper(),
                "champion": champion_id.upper(),
                "desired_output_fields": self.CHAMPION_LEADERBOARD_OUTPUT_FIELDS,
            },
        )

    def _call_tool(self, tool_name: str, arguments: dict[str, Any]) -> str:
        cache_key = self._build_cache_key(tool_name, arguments)
        if cache_key in self._response_cache:
            return self._response_cache[cache_key]

        process = subprocess.Popen(
            self._node_command,
            cwd=self._mcp_dir,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )

        try:
            self._send(
                process,
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {
                            "name": "lol-chatbot-api",
                            "version": "0.1.0",
                        },
                    },
                },
            )
            self._read_until_id(process, 1)
            self._send(
                process,
                {
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized",
                    "params": {},
                },
            )
            self._send(
                process,
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {
                        "name": tool_name,
                        "arguments": arguments,
                    },
                },
            )
            response = self._read_until_id(process, 2)
        finally:
            process.terminate()

        if "error" in response:
            raise RuntimeError(response["error"].get("message", "OP.GG MCP 호출 실패"))

        contents = response.get("result", {}).get("content", [])
        if not contents:
            raise RuntimeError("OP.GG MCP 응답 본문이 비어 있습니다.")

        result_text = str(contents[0].get("text", ""))
        self._response_cache[cache_key] = result_text
        return result_text

    def _build_cache_key(self, tool_name: str, arguments: dict[str, Any]) -> str:
        return json.dumps(
            {
                "tool_name": tool_name,
                "arguments": arguments,
            },
            ensure_ascii=False,
            sort_keys=True,
        )

    def _send(
        self,
        process: subprocess.Popen[str],
        payload: dict[str, Any],
    ) -> None:
        if process.stdin is None:
            raise RuntimeError("OP.GG MCP 표준 입력을 열 수 없습니다.")

        process.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
        process.stdin.flush()

    def _read_until_id(
        self,
        process: subprocess.Popen[str],
        message_id: int,
    ) -> dict[str, Any]:
        if process.stdout is None:
            raise RuntimeError("OP.GG MCP 표준 출력을 열 수 없습니다.")

        while True:
            line = process.stdout.readline()
            if not line:
                stderr = process.stderr.read() if process.stderr is not None else ""
                raise RuntimeError(
                    "OP.GG MCP 응답을 읽지 못했습니다."
                    f" stderr: {stderr.strip()}"
                )

            message = json.loads(line)
            if message.get("id") == message_id:
                return message

    def _parse_champion_analysis(self, text: str) -> dict[str, Any]:
        champion_match = re.search(
            r'LolGetChampionAnalysis\("([^"]+)","([^"]+)",Data\(',
            text,
        )
        champion = champion_match.group(1) if champion_match else ""
        position = champion_match.group(2) if champion_match else ""

        runes = self._parse_runes(text)
        spell_groups = self._parse_spell_like_groups(text)
        skill_masteries = self._parse_skill_masteries(text)
        skills = self._parse_skills(text)
        easy_counters, difficult_counters = self._parse_counter_groups(text)
        difficult_counters = sorted(
            difficult_counters,
            key=lambda counter: counter.get("win_rate", 0),
        )
        easy_counters = sorted(
            easy_counters,
            key=lambda counter: counter.get("win_rate", 0),
            reverse=True,
        )

        return {
            "champion": champion,
            "position": position,
            "runes": runes,
            "summoner_spells": spell_groups[0] if len(spell_groups) > 0 else {},
            "starter_items": spell_groups[1] if len(spell_groups) > 1 else {},
            "boots": spell_groups[2] if len(spell_groups) > 2 else {},
            "core_items": spell_groups[3] if len(spell_groups) > 3 else {},
            "skill_masteries": skill_masteries,
            "skills": skills,
            "strong_counters": difficult_counters[:5],
            "weak_counters": easy_counters[:5],
            "raw_text": text,
        }

    def _parse_item_analysis(self, text: str) -> dict[str, Any]:
        champion_match = re.search(
            r'LolGetChampionAnalysis\("([^"]+)","([^"]+)",Data\(',
            text,
        )
        champion = champion_match.group(1) if champion_match else ""
        position = champion_match.group(2) if champion_match else ""
        item_groups = self._parse_spell_like_groups(text)

        return {
            "champion": champion,
            "position": position,
            "runes": {},
            "summoner_spells": {},
            "starter_items": item_groups[0] if len(item_groups) > 0 else {},
            "boots": item_groups[1] if len(item_groups) > 1 else {},
            "core_items": item_groups[2] if len(item_groups) > 2 else {},
            "skill_masteries": {},
            "skills": {},
            "strong_counters": [],
            "weak_counters": [],
            "raw_text": text,
        }

    def _parse_champions(self, text: str) -> list[dict[str, Any]]:
        champions = []
        for match in re.finditer(
            r'Champion\((\d+),"([^"]+)","([^"]+)"(?:,"([^"]+)")?\)',
            text,
        ):
            champion_id = match.group(1)
            key = match.group(2)
            name = match.group(3)
            champions.append(
                {
                    "champion_id": champion_id,
                    "key": key,
                    "name_ko": name,
                    "name_en": key,
                    "release_date": match.group(4) or "",
                }
            )
        return champions

    def _parse_lane_meta_champions(
        self,
        text: str,
        position: str,
    ) -> list[dict[str, Any]]:
        class_name = {
            "top": "Top",
            "jungle": "Jungle",
            "mid": "Mid",
            "adc": "Adc",
            "support": "Support",
        }.get(position, "Mid")
        pattern = (
            rf'{class_name}\("([^"]+)",([\d.]+),([\d.]+),([\d.]+),'
            rf'(\d+),(\d+),([\d.]+),(\d+),([\d.]+)\)'
        )

        champions = []
        for match in re.finditer(pattern, text):
            champions.append(
                {
                    "name_ko": match.group(1),
                    "win_rate": self._to_percentage(float(match.group(2))),
                    "pick_rate": self._to_percentage(float(match.group(3))),
                    "ban_rate": self._to_percentage(float(match.group(4))),
                    "tier": int(match.group(5)),
                    "rank": int(match.group(6)),
                    "kda": float(match.group(7)),
                    "play": int(match.group(8)),
                    "role_rate": self._to_percentage(float(match.group(9))),
                    "position": position.upper(),
                }
            )
        if champions:
            return champions

        for match in re.finditer(rf'{class_name}\("([^"]+)"\)', text):
            champions.append(
                {
                    "name_ko": match.group(1),
                    "rank": 0,
                    "tier": 0,
                    "win_rate": 0.0,
                    "pick_rate": 0.0,
                    "ban_rate": 0.0,
                    "kda": 0.0,
                    "play": 0,
                    "role_rate": 0.0,
                    "position": position.upper(),
                }
            )
        return champions

    def _parse_runes(self, text: str) -> dict[str, Any]:
        match = re.search(
            r'Runes\("([^"]+)",(\[.*?\]),"([^"]+)",(\[.*?\]),(\[.*?\]),([\d.]+),(\d+),(\d+)\)',
            text,
        )
        if not match:
            return {}

        return {
            "primary_page_name": match.group(1),
            "primary_rune_names": self._literal_list(match.group(2)),
            "secondary_page_name": match.group(3),
            "secondary_rune_names": self._literal_list(match.group(4)),
            "stat_mod_names": self._literal_list(match.group(5)),
            "pick_rate": float(match.group(6)),
            "play": int(match.group(7)),
            "win": int(match.group(8)),
        }

    def _parse_spell_like_groups(self, text: str) -> list[dict[str, Any]]:
        groups = []
        for match in re.finditer(
            r"(?:SummonerSpells|StarterItems|Boots|CoreItems)\((\[.*?\]),(\[.*?\]),(\d+),(\d+),([\d.]+)\)",
            text,
        ):
            groups.append(
                {
                    "ids": self._literal_list(match.group(1)),
                    "ids_names": self._literal_list(match.group(2)),
                    "play": int(match.group(3)),
                    "win": int(match.group(4)),
                    "pick_rate": float(match.group(5)),
                }
            )
        return groups

    def _parse_skill_masteries(self, text: str) -> dict[str, Any]:
        match = re.search(
            r"SkillMasteries\((\[.*?\]),(\d+),(\d+),([\d.]+)\)",
            text,
        )
        if not match:
            return {}

        return {
            "ids": self._literal_list(match.group(1)),
            "play": int(match.group(2)),
            "win": int(match.group(3)),
            "pick_rate": float(match.group(4)),
        }

    def _parse_skills(self, text: str) -> dict[str, Any]:
        match = re.search(
            r"Skills\((\[.*?\]),(\d+),(\d+),([\d.]+)\)",
            text,
        )
        if not match:
            return {}

        return {
            "order": self._literal_list(match.group(1)),
            "play": int(match.group(2)),
            "win": int(match.group(3)),
            "pick_rate": float(match.group(4)),
        }

    def _parse_counter_groups(
        self,
        text: str,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        match = re.search(
            r"Data\(Summary\(AverageStats\([^)]*\)\),\[(.*?)\],\[(.*?)\]\)",
            text,
        )
        if not match:
            return [], []

        easy_counters = self._parse_counters(match.group(1))
        difficult_counters = self._parse_counters(match.group(2))
        return easy_counters, difficult_counters

    def _parse_champion_synergies(self, text: str) -> dict[str, Any]:
        synergy_match = re.search(
            r'LolGetChampionSynergies\("([^"]+)","([^"]+)","([^"]+)",Data\(',
            text,
        )
        champion = synergy_match.group(1) if synergy_match else ""
        my_position = synergy_match.group(2) if synergy_match else ""
        synergy_position = synergy_match.group(3) if synergy_match else ""
        synergies = self._parse_synergies(text)
        total_play = sum(synergy["play"] for synergy in synergies)

        for synergy in synergies:
            play_share = synergy["play"] / total_play if total_play else 0.0
            synergy["play_share"] = play_share
            synergy["recommend_score"] = synergy["win_rate"] * 0.7 + play_share * 0.3

        synergies.sort(
            key=lambda synergy: (
                synergy["recommend_score"],
                synergy["win_rate"],
                synergy["play"],
            ),
            reverse=True,
        )
        return {
            "champion": champion,
            "my_position": my_position,
            "synergy_position": synergy_position,
            "synergies": synergies,
            "raw_text": text,
        }

    def _parse_synergies(self, text: str) -> list[dict[str, Any]]:
        synergies = []
        for match in re.finditer(
            r'Synergie\((\d+),"([^"]+)",(\d+),"([^"]+)",([\d.]+),(\d+),'
            r'(\d+),"([^"]+)","([^"]+)",(\d+),([\d.]+),'
            r"SynergyTierData\((\d+),(\d+)\)\)",
            text,
        ):
            play = int(match.group(3))
            win = int(match.group(10))
            synergies.append(
                {
                    "champion_id": match.group(1),
                    "champion_name": match.group(2),
                    "play": play,
                    "position": match.group(4),
                    "score": float(match.group(5)),
                    "score_rank": int(match.group(6)),
                    "synergy_champion_id": match.group(7),
                    "synergy_champion_name": match.group(8),
                    "synergy_position": match.group(9),
                    "win": win,
                    "win_rate": self._normalize_rate(float(match.group(11))),
                    "calculated_win_rate": win / play if play else 0.0,
                    "synergy_tier_rank": int(match.group(12)),
                    "synergy_tier": int(match.group(13)),
                }
            )
        return synergies

    def _parse_counters(self, text: str) -> list[dict[str, Any]]:
        counters = []
        for match in re.finditer(
            r'StrongCounter\((\d+),"([^"]+)",(\d+),(\d+),([\d.]+)\)',
            text,
        ):
            play = int(match.group(3))
            win = int(match.group(4))
            counters.append(
                {
                    "champion_id": match.group(1),
                    "champion_name": match.group(2),
                    "play": play,
                    "win": win,
                    "win_rate": win / play if play else 0.0,
                    "source_win_rate": self._normalize_rate(float(match.group(5))),
                }
            )
        return counters

    def _normalize_rate(self, value: float) -> float:
        if value > 1:
            return value / 100
        return value

    def _to_percentage(self, value: float) -> float:
        if value <= 1:
            return round(value * 100, 2)
        return round(value, 2)

    def _literal_list(self, value: str) -> list[Any]:
        parsed = ast.literal_eval(value)
        return parsed if isinstance(parsed, list) else []
