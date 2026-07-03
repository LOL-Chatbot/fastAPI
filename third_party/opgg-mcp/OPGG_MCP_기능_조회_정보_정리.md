# OP.GG MCP 기능 및 조회 가능 정보 정리

## 작성 정보

- 작성자: 김진우
- 작성일: 2026-06-30
- 대상 저장소: `C:\Users\jinwo\Documents\opgg\opgg-mcp`

## Reference 폴더 점검 결과

요청 지침에 따라 응답 및 문서 작성 전에 `Reference` 폴더의 API 명세서, 시스템 아키텍처, 요구사항, DB 설계 관련 md 파일을 우선 점검하려고 했습니다.

하지만 현재 작업 루트인 `C:\Users\jinwo\Documents\opgg` 기준으로 `Reference` 폴더 내 파일이 조회되지 않았습니다. 따라서 필수 점검 항목은 실제 파일 기준으로 확인할 수 없었습니다.

이번 문서는 다음 파일 및 자료를 기준으로 작성했습니다.

- `opgg-mcp/README.md`
- `opgg-mcp/README.ko.md`
- `opgg-mcp/AGENTS.md`
- `opgg-mcp/src/index.ts`
- `opgg-mcp/MCP_tool_test_summary.md`
- `opgg-mcp/ANNIE_tool_test.txt`
- GitHub 원격 저장소 `opgginc/opgg-mcp`의 최신 `README.md`

## 1. OP.GG MCP 개요

OP.GG MCP Server는 AI 에이전트가 OP.GG의 게임 데이터를 조회할 수 있도록 제공되는 Model Context Protocol 서버입니다.

조회 가능한 주요 게임 영역은 다음과 같습니다.

| 영역 | 조회 가능 정보 |
| --- | --- |
| 리그 오브 레전드 | 챔피언 분석, 라인 메타, 소환사 프로필, 매치 기록, 아이템, 스킨 할인, 프로 선수, e스포츠 일정 및 순위 |
| 전략적 팀 전투 | 챔피언 아이템 빌드, 플레이 스타일, 증강, 아이템 조합, 메타 덱 |
| 발로란트 | 요원 정보, 요원 통계, 맵, 조합, 리더보드, 플레이어 매치 기록 |

현재 로컬 저장소는 OP.GG MCP 기능을 직접 구현하는 서버가 아니라, 원격 OP.GG MCP 서버를 stdio 방식으로 연결해 주는 프록시입니다.

원격 MCP 엔드포인트는 다음과 같습니다.

```text
https://mcp-api.op.gg/mcp
```

`src/index.ts`에서는 위 원격 엔드포인트에 `StreamableHTTPClientTransport`로 연결한 뒤, 로컬 MCP 클라이언트가 사용할 수 있도록 `StdioServerTransport`로 프록시합니다.

## 2. 공통 사용 방식

대부분의 OP.GG MCP 도구는 `desired_output_fields` 파라미터를 사용합니다.

이 값은 응답에서 받고 싶은 필드만 선택하기 위한 기능입니다. OP.GG 데이터는 응답 크기가 클 수 있으므로 필요한 필드만 지정하면 응답 크기를 줄이고 해석 효율을 높일 수 있습니다.

### 2.1 필드 선택 문법

| 문법 | 의미 | 예시 |
| --- | --- | --- |
| `field` | 단일 필드 선택 | `name` |
| `parent.child` | 중첩 필드 선택 | `data.summoner.level` |
| `array[]` | 배열 전체 선택 | `champions[]` |
| `array[].field` | 배열 항목 내부 필드 선택 | `data.champions[].name` |
| `{a,b,c}` | 같은 레벨의 여러 필드 선택 | `{name,title,lore}` |
| `parent.{a,b}` | 중첩 객체의 여러 필드 선택 | `data.summoner.{level,name}` |
| `array[].{a,b}` | 배열 항목 내부 여러 필드 선택 | `data.champions[].{name,title}` |

### 2.2 필드 선택 예시

```json
{
  "desired_output_fields": [
    "data.summoner.{game_name,tagline,level}",
    "data.summoner.league_stats[].{game_type,win,lose}",
    "data.summoner.league_stats[].tier_info.{tier,division,lp}"
  ]
}
```

위 예시는 소환사 정보 중 게임 이름, 태그라인, 레벨, 랭크 게임별 승패, 티어, 디비전, LP만 조회하도록 요청하는 방식입니다.

## 3. 리그 오브 레전드 조회 기능

### 3.1 챔피언 관련 기능

| MCP 도구 | 조회 가능 정보 | 활용 예시 |
| --- | --- | --- |
| `lol_get_champion_analysis` | 챔피언 상세 통계, 승률, 픽률, 밴률, 최적 아이템 빌드, 룬, 스킬, 소환사 주문, 카운터 매치업, 팀 시너지 | 특정 챔피언의 현재 메타 성능 분석 |
| `lol_get_champion_synergies` | 특정 챔피언과 함께 사용하기 좋은 챔피언 시너지 정보 | 듀오 조합, 팀 조합 추천 |
| `lol_get_lane_matchup_guide` | 특정 라인 기준 매치업 가이드 | 라인전 상대별 운영 방법 확인 |
| `lol_list_champion_details` | 최대 10개 챔피언의 스킬, 팁, 배경 이야기, 스탯 메타데이터 | 챔피언 기본 정보 조회 |
| `lol_list_champion_leaderboard` | 챔피언 리더보드 데이터 | 챔피언별 상위권 플레이어 또는 순위 데이터 확인 |
| `lol_list_champions` | 전체 챔피언 메타데이터 목록 | 챔피언 목록, 이름, 식별자 조회 |
| `lol_list_lane_meta_champions` | 라인별 챔피언 티어, 승률, 픽률, 밴률, KDA, 티어 랭킹 | 현재 라인별 메타 챔피언 확인 |

`lol_get_champion_analysis`는 가장 종합적인 챔피언 분석 도구입니다. 기존 `ANNIE_tool_test.txt` 기준으로 확인된 응답 구조에는 다음과 같은 정보가 포함될 수 있습니다.

- 챔피언과 포지션
- 요약 통계
- 피해 유형
- 강한 상대와 약한 상대
- 시너지 챔피언
- 시작 아이템, 신발, 코어 아이템, 후반 아이템
- 소환사 주문
- 룬
- 스킬 순서
- 스킬 콤보
- 스킬 마스터리
- 트렌드

### 3.2 소환사 관련 기능

| MCP 도구 | 조회 가능 정보 | 활용 예시 |
| --- | --- | --- |
| `lol_get_summoner_game_detail` | 특정 경기의 상세 정보와 모든 플레이어 정보 | 한 경기의 상세 분석 |
| `lol_get_summoner_profile` | 소환사 프로필, 랭크, 티어, LP, 승률, 챔피언 풀 | 특정 플레이어 전적 및 랭크 확인 |
| `lol_list_summoner_matches` | 최근 매치 기록과 경기별 통계 | 최근 전적 분석, 연승/연패 흐름 확인 |

### 3.3 리소스 관련 기능

| MCP 도구 | 조회 가능 정보 | 활용 예시 |
| --- | --- | --- |
| `lol_list_discounted_skins` | 현재 할인 중인 스킨 목록 | 스킨 할인 정보 확인 |
| `lol_list_items` | 전체 아이템 메타데이터 | 아이템 목록, 아이템 정보 조회 |

### 3.4 프로 선수 관련 기능

| MCP 도구 | 조회 가능 정보 | 활용 예시 |
| --- | --- | --- |
| `lol_get_pro_player_riot_id` | 프로 선수의 Riot ID | 프로 선수 계정 검색 |

### 3.5 e스포츠 관련 기능

| MCP 도구 | 조회 가능 정보 | 활용 예시 |
| --- | --- | --- |
| `lol_esports_list_schedules` | LoL e스포츠 일정, 팀, 리그, 경기 시간 | 예정 경기 확인 |
| `lol_esports_list_team_standings` | LoL 리그 팀 순위 | 리그별 순위 확인 |

## 4. 전략적 팀 전투 조회 기능

| MCP 도구 | 조회 가능 정보 | 활용 예시 |
| --- | --- | --- |
| `tft_get_champion_item_build` | 챔피언별 추천 아이템 빌드 | 특정 기물의 최적 아이템 확인 |
| `tft_get_play_style` | 플레이 스타일 추천 | 성향 또는 상황에 맞는 운영 방식 확인 |
| `tft_list_augments` | 증강 목록과 설명 | 증강 효과 확인 |
| `tft_list_champions_for_item` | 특정 아이템에 적합한 챔피언 추천 | 아이템이 먼저 나왔을 때 사용할 기물 선택 |
| `tft_list_item_combinations` | 아이템 조합식 | 완성 아이템 제작법 확인 |
| `tft_list_meta_decks` | 현재 메타 덱 | 유행 덱과 추천 덱 확인 |

## 5. 발로란트 조회 기능

| MCP 도구 | 조회 가능 정보 | 활용 예시 |
| --- | --- | --- |
| `valorant_list_agent_compositions_for_map` | 특정 맵의 요원 조합 | 맵별 추천 조합 확인 |
| `valorant_list_agent_statistics` | 요원 통계와 메타 데이터 | 요원별 성능 분석 |
| `valorant_list_agents` | 요원 메타데이터, 능력, 역할 | 요원 기본 정보 확인 |
| `valorant_list_leaderboard` | 지역별 리더보드 | 지역 랭킹 확인 |
| `valorant_list_maps` | 맵 메타데이터 | 맵 목록과 정보 확인 |
| `valorant_list_player_matches` | 플레이어 매치 기록 | 특정 플레이어 최근 경기 확인 |

`valorant_list_leaderboard`에서 확인 가능한 지역 값은 다음과 같습니다.

- `ap`
- `br`
- `eu`
- `kr`
- `latam`
- `na`

## 6. 전체 MCP 도구 목록

현재 README와 원격 GitHub README 기준으로 확인되는 OP.GG MCP 도구는 총 27개입니다.

| 번호 | 도구명 | 영역 |
| --- | --- | --- |
| 1 | `lol_get_champion_analysis` | 리그 오브 레전드 |
| 2 | `lol_get_champion_synergies` | 리그 오브 레전드 |
| 3 | `lol_get_lane_matchup_guide` | 리그 오브 레전드 |
| 4 | `lol_list_champion_details` | 리그 오브 레전드 |
| 5 | `lol_list_champion_leaderboard` | 리그 오브 레전드 |
| 6 | `lol_list_champions` | 리그 오브 레전드 |
| 7 | `lol_list_lane_meta_champions` | 리그 오브 레전드 |
| 8 | `lol_get_summoner_game_detail` | 리그 오브 레전드 |
| 9 | `lol_get_summoner_profile` | 리그 오브 레전드 |
| 10 | `lol_list_summoner_matches` | 리그 오브 레전드 |
| 11 | `lol_list_discounted_skins` | 리그 오브 레전드 |
| 12 | `lol_list_items` | 리그 오브 레전드 |
| 13 | `lol_get_pro_player_riot_id` | 리그 오브 레전드 |
| 14 | `lol_esports_list_schedules` | 리그 오브 레전드 |
| 15 | `lol_esports_list_team_standings` | 리그 오브 레전드 |
| 16 | `tft_get_champion_item_build` | 전략적 팀 전투 |
| 17 | `tft_get_play_style` | 전략적 팀 전투 |
| 18 | `tft_list_augments` | 전략적 팀 전투 |
| 19 | `tft_list_champions_for_item` | 전략적 팀 전투 |
| 20 | `tft_list_item_combinations` | 전략적 팀 전투 |
| 21 | `tft_list_meta_decks` | 전략적 팀 전투 |
| 22 | `valorant_list_agent_compositions_for_map` | 발로란트 |
| 23 | `valorant_list_agent_statistics` | 발로란트 |
| 24 | `valorant_list_agents` | 발로란트 |
| 25 | `valorant_list_leaderboard` | 발로란트 |
| 26 | `valorant_list_maps` | 발로란트 |
| 27 | `valorant_list_player_matches` | 발로란트 |

## 7. 기능 관점 요약

OP.GG MCP로 할 수 있는 일은 다음과 같이 정리할 수 있습니다.

| 기능 범주 | 설명 |
| --- | --- |
| 메타 분석 | LoL 라인별 챔피언 티어, TFT 메타 덱, 발로란트 요원 통계처럼 현재 메타를 조회할 수 있습니다. |
| 플레이어 분석 | LoL 소환사 프로필과 매치 기록, 발로란트 플레이어 매치 기록을 조회할 수 있습니다. |
| 빌드 추천 | LoL 챔피언 아이템, 룬, 스킬, 스펠과 TFT 챔피언 아이템 빌드를 조회할 수 있습니다. |
| 매치업 분석 | LoL 챔피언 카운터, 강한 상대, 약한 상대, 라인 매치업 가이드를 조회할 수 있습니다. |
| 조합 분석 | LoL 챔피언 시너지, 발로란트 맵별 요원 조합을 조회할 수 있습니다. |
| 정적 리소스 조회 | LoL 챔피언, 아이템, 스킨 할인, TFT 증강, 아이템 조합, 발로란트 요원과 맵 정보를 조회할 수 있습니다. |
| e스포츠 조회 | LoL e스포츠 일정과 리그 팀 순위를 조회할 수 있습니다. |
| 프로 선수 조회 | LoL 프로 선수의 Riot ID를 조회할 수 있습니다. |

## 8. 로컬 프록시 구조상 주의사항

현재 저장소는 원격 OP.GG MCP 서버의 도구 정의를 로컬에서 새로 선언하지 않습니다.

`AGENTS.md` 기준으로 이 저장소는 원격 MCP 서버를 stdio로 연결하는 얇은 프록시입니다. 따라서 도구 목록과 스키마의 실제 기준은 원격 엔드포인트인 `https://mcp-api.op.gg/mcp`입니다.

주의할 점은 다음과 같습니다.

- 로컬 코드에 MCP 도구를 직접 추가하지 않습니다.
- 도구 목록이 바뀌면 6개 언어 README를 함께 갱신해야 합니다.
- 원격 서버의 도구 스키마가 바뀌면 로컬 문서와 실제 도구 목록이 달라질 수 있습니다.
- 대부분의 조회 도구는 `desired_output_fields`를 적절히 지정해야 응답을 효율적으로 받을 수 있습니다.

## 9. 결론

OP.GG MCP는 리그 오브 레전드, 전략적 팀 전투, 발로란트 데이터를 조회하는 게임 데이터 MCP입니다.

현재 확인 가능한 도구는 총 27개이며, 리그 오브 레전드는 챔피언 분석과 소환사 전적, e스포츠 데이터까지 가장 넓은 범위를 지원합니다. TFT는 메타 덱과 아이템 중심의 추천 기능을 제공하고, 발로란트는 요원, 맵, 조합, 리더보드, 플레이어 매치 기록 조회에 초점이 맞춰져 있습니다.

이 문서는 `Reference` 폴더의 필수 md 파일이 현재 조회되지 않는 상태에서 작성되었으므로, 추후 `Reference` 폴더가 추가되면 API 명세서, 시스템 아키텍처, 요구사항, DB 설계 문서와 다시 대조하는 것이 좋습니다.
