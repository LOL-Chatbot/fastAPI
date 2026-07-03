# OP.GG MCP 프록시 수정 및 Tool 테스트 정리

## 작성 정보

- 작성자: 김진우
- 작성일: 2026-06-25
- 대상 저장소: `C:\Users\jinwo\Documents\opgg\opgg-mcp`

## 참조 파일

이번 정리와 작업 판단에 참조한 파일은 다음과 같습니다.

- `AGENTS.md`
- `README.md`
- `README.ko.md`
- `package.json`
- `src/index.ts`
- `src/proxy-server.ts`
- `dist/index.js`
- `ANNIE_tool_test.txt`
- `node_modules/@modelcontextprotocol/sdk/dist/esm/types.js`
- `node_modules/@modelcontextprotocol/sdk/dist/esm/shared/protocol.d.ts`
- `node_modules/@modelcontextprotocol/sdk/dist/esm/server/index.js`

`Reference` 폴더는 현재 저장소 루트에 존재하지 않았습니다.
따라서 AGENTS 지시의 필수 점검 항목인 API 명세서, 시스템 아키텍처, 요구사항, DB 설계 관련 md 파일은 실제 파일 기준으로 확인할 수 없었습니다.

## 1. 최초 오류

MCP 서버 알림에 다음 오류가 발생했습니다.

```text
could not start the proxy Error: Server does not support completions (required for completion/complete)
```

원인은 `src/proxy-server.ts`에서 원격 서버가 `completions` capability를 제공하지 않아도 `CompleteRequestSchema` 핸들러를 무조건 등록했기 때문입니다.

MCP SDK는 서버 capability에 `completions`가 없는데 `completion/complete` 요청 핸들러가 등록되면 시작을 중단합니다.

## 2. completions 오류 수정

수정 전에는 completion 핸들러가 항상 등록되었습니다.

수정 후에는 원격 OP.GG MCP 서버가 `completions` capability를 제공할 때만 핸들러를 등록하도록 변경했습니다.

```ts
if (serverCapabilities?.completions) {
  server.setRequestHandler(CompleteRequestSchema, async (args) => {
    return client.complete(args.params);
  });
}
```

수정 파일:

- `src/proxy-server.ts`

효과:

- 원격 서버가 completions를 지원하지 않아도 프록시가 정상 시작됩니다.
- 원격 서버가 completions를 지원하는 경우에는 기존처럼 `completion/complete` 요청을 전달합니다.

## 3. 빌드 및 실행 확인

수정 후 다음 검증을 수행했습니다.

```text
tsc --noEmit 성공
tsup 빌드 성공
dist/index.js 반영 완료
```

사용자 환경에서는 `pnpm` 명령이 등록되어 있지 않아 다음 명령은 실패했습니다.

```powershell
pnpm build
```

또한 `npm build`는 올바른 npm 명령이 아니므로 실패했습니다.
사용하려면 다음 형식이 맞습니다.

```powershell
npm run build
```

다만 프로젝트 규칙상 패키지 매니저는 `pnpm` 사용이 권장됩니다.

실행 확인:

```powershell
node dist/index.js
```

실행 후 다음 메시지가 출력되었습니다.

```text
SIGINT received, shutting down
```

이는 일반적으로 사용자가 `Ctrl+C`로 프로세스를 종료했을 때 나오는 메시지입니다.
기존 completions 오류가 다시 나오지 않았다면 첫 번째 수정은 정상 반영된 것으로 볼 수 있습니다.

## 4. tools/list 오류

Tool 목록 조회 시 다음 오류가 발생했습니다.

```json
{
  "error": "MCP error -32603: [
    {
      \"code\": \"invalid_value\",
      \"values\": [
        \"object\"
      ],
      \"path\": [
        \"tools\",
        26,
        \"outputSchema\",
        \"type\"
      ],
      \"message\": \"Invalid input: expected \\\"object\\\"\"
    },
    {
      \"code\": \"invalid_value\",
      \"values\": [
        \"object\"
      ],
      \"path\": [
        \"tools\",
        28,
        \"outputSchema\",
        \"type\"
      ],
      \"message\": \"Invalid input: expected \\\"object\\\"\"
    }
  ]"
}
```

의미:

- 원격 OP.GG MCP 서버가 내려준 tool 목록 중 27번째, 29번째 도구의 `outputSchema.type` 값이 MCP SDK 기준에 맞지 않았습니다.
- MCP SDK의 `ToolSchema`는 `outputSchema.type`의 최상위 값을 반드시 `"object"`로 요구합니다.
- 이 문제는 원격 tool 정의의 스키마 문제이며, 로컬 프록시는 원격 응답을 그대로 전달하고 있었기 때문에 함께 실패했습니다.

## 5. tools/list 임시 우회 조치

정석 해결은 원격 OP.GG MCP 서버의 tool 정의를 수정하는 것입니다.

하지만 로컬 테스트를 계속하기 위해 임시 우회 조치를 적용했습니다.

적용 방식:

- `client.listTools()`를 직접 호출하지 않습니다.
- 대신 `client.request()`와 느슨한 Zod 스키마를 사용해 `tools/list` 응답을 먼저 받습니다.
- 각 tool의 `outputSchema`를 검사합니다.
- `outputSchema.type`이 `"object"`가 아니면 `"object"`로 보정합니다.
- `outputSchema`가 객체가 아니면 해당 `outputSchema`를 제거합니다.

수정 파일:

- `src/proxy-server.ts`

검증 결과:

```text
tsc --noEmit 성공
tsup 빌드 성공
dist/index.js 반영 완료
```

주의:

- 이 조치는 원격 MCP 서버의 잘못된 tool 정의를 로컬 프록시에서 보정하는 임시 우회입니다.
- 장기적으로는 원격 OP.GG MCP 서버의 해당 tool `outputSchema`를 MCP 규격에 맞게 수정하는 것이 맞습니다.

## 6. desired_output_fields 의미 확인

Tool 입력 중 `desired_output_fields`는 응답에서 받고 싶은 필드만 선택하는 필수 입력값입니다.

의미:

```text
응답 전체를 받지 말고, 필요한 데이터 필드만 골라서 받는다.
```

이유:

- OP.GG 챔피언 분석 데이터는 크기가 큽니다.
- 필요한 필드만 받으면 응답 크기가 줄고 테스트와 해석이 쉬워집니다.

예시:

```json
{
  "desired_output_fields": [
    "champion",
    "position",
    "data.runes.{primary_page_name,primary_rune_names[],secondary_page_name,secondary_rune_names[],stat_mod_names[],pick_rate,play,win}"
  ]
}
```

위 입력은 챔피언, 포지션, 룬 이름, 룬 픽률, 플레이 수, 승리 수만 받겠다는 의미입니다.

## 7. 애니 Tool 테스트 결과

`ANNIE_tool_test.txt`에는 `lol_get_champion_analysis` 도구로 조회한 미드 애니 분석 응답이 저장되어 있었습니다.

요청 대상:

- 챔피언: `ANNIE`
- 포지션: `MID`

핵심 해석:

- 전체 통계: `6137`판
- 전체 승률: `49%`
- 전체 픽률: `3%`
- 전체 밴률: `1%`
- 전체 KDA: `2.11`
- 전체 티어: `5티어`
- 전체 랭킹: `158위`

미드 포지션 기준:

- 미드 판수: `5106`판
- 미드 승률: `50%`
- 미드 픽률: `2%`
- 미드 밴률: `1%`
- 미드 KDA: `2.13`
- 미드 티어: `4티어`
- 미드 랭킹: `32위`

요약하면 애니는 전체적으로 강한 OP 픽이라기보다는, 미드에서 무난하게 사용할 수 있는 챔피언으로 해석됩니다.

## 8. 애니 추천 룬

응답 기준 추천 룬은 다음과 같습니다.

```text
주 룬: 지배
핵심 룬: 감전
보조 룬: 마법
```

세부 룬:

```text
지배
- 감전
- 비열한 한 방
- Grisly Mementos
- 끈질긴 사냥꾼

마법
- Axiom Arcanist
- 절대 집중
```

룬 통계:

- 사용 판수: `1388`판
- 승리 수: `675`승
- 픽률: `43%`
- 계산상 승률: 약 `48.6%`

## 9. 애니 추천 아이템

시작 아이템:

```text
도란의 반지 + 체력 물약 2개
```

신발:

```text
마법사의 신발
```

핵심 3코어:

```text
Malignance
Hextech Rocketbelt
Shadowflame
```

해석:

```text
악의
마법공학 로켓 벨트
그림자불꽃
```

3코어 통계:

- 사용 판수: `370`판
- 승리 수: `187`승
- 픽률: `19%`
- 계산상 승률: 약 `50.5%`

## 10. 애니 추천 스킬 및 스펠

스킬 마스터 순서:

```text
Q > W > E
```

레벨별 추천 순서:

```text
Q - W - E - Q - Q - R - Q - W - Q - W - R - W - W - E - E
```

소환사 주문:

```text
점멸 + 점화
```

응답에는 소환사 주문 ID가 `[4, 14]`로 제공되었습니다.
이는 일반적으로 점멸과 점화 조합으로 해석할 수 있습니다.

## 11. 애니 상성

애니가 상대하기 까다로운 챔피언:

```text
야스오
신드라
```

애니가 상대하기 좋은 챔피언:

```text
카타리나
사일러스
빅토르
```

응답 기준 애니의 상대별 승률:

- 카타리나 상대: `57%`
- 사일러스 상대: `55%`
- 빅토르 상대: `53%`

## 12. 애니와 잘 맞는 아군

탑:

```text
갱플랭크
크산테
제이스
```

정글:

```text
오공
신 짜오
사일러스
```

원딜:

```text
애쉬
징크스
케이틀린
```

서포터:

```text
레오나
유미
바드
```

특히 레오나는 응답 기준 승률이 높게 나왔지만 표본이 `26`판이므로 참고용으로 보는 것이 좋습니다.

## 13. 현재 상태

완료된 작업:

- completions capability 오류 수정
- `tools/list`의 `outputSchema.type` 오류 임시 우회
- TypeScript 타입체크 성공
- 빌드 성공
- `dist/index.js` 반영 확인
- `desired_output_fields` 사용법 확인
- 애니 챔피언 분석 응답 해석

남은 권장 작업:

- OP.GG 원격 MCP 서버 쪽의 잘못된 tool `outputSchema` 정식 수정
- 사용자 PC에서 `pnpm` 명령 사용 가능하도록 설정
- 실제 MCP 클라이언트 또는 IDE에서 tool list 재조회
- 필요한 챔피언별 `desired_output_fields` 예시 문서화

## 14. 한 줄 요약

로컬 프록시는 이제 시작 오류와 tool list 검증 오류를 우회할 수 있으며, 애니 챔피언 분석 tool 응답도 정상적으로 해석 가능한 상태입니다.
