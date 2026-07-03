# completions capability 오류 수정 요청

## 현상

서버 시작 중 다음 오류가 발생합니다.

```text
Server does not support completions (required for completion/complete)
```

## 확인한 파일

- `AGENTS.md`
- `src/index.ts`
- `src/proxy-server.ts`
- `package.json`
- `node_modules/@modelcontextprotocol/sdk/dist/esm/server/index.js`
- `node_modules/@modelcontextprotocol/sdk/dist/esm/spec.types.d.ts`

## Reference 폴더 점검 결과

현재 저장소 루트에는 `Reference` 폴더가 존재하지 않습니다.
따라서 AGENTS 지시의 필수 점검 항목인 API 명세서, 시스템 아키텍처, 요구사항, DB 설계 관련 md 파일은 실제 파일 기준으로 확인할 수 없었습니다.

대신 현재 저장소에 존재하는 `AGENTS.md`와 소스 코드, MCP SDK 타입 정의를 기준으로 원인을 판단했습니다.

## 원인

`src/proxy-server.ts`에서 `CompleteRequestSchema` 요청 핸들러를 원격 서버 capability 확인 없이 항상 등록하고 있습니다.

하지만 `src/index.ts`는 원격 OP.GG MCP 서버가 반환한 capability를 그대로 stdio 서버 capability로 전달합니다.
원격 서버 capability에 `completions`가 없으면, MCP SDK의 `Server.setRequestHandler(CompleteRequestSchema, ...)` 호출 시 서버가 `completion/complete`를 지원하지 않는다고 판단하여 시작을 중단합니다.

## 수정 제안

`src/proxy-server.ts`의 completion 핸들러 등록을 다음 조건으로 감쌉니다.

```ts
if (serverCapabilities?.completions) {
  server.setRequestHandler(CompleteRequestSchema, async (args) => {
    return client.complete(args.params);
  });
}
```

## 기대 효과

- 원격 OP.GG MCP 서버가 completions를 제공하지 않는 경우에도 프록시가 정상 시작됩니다.
- 원격 서버가 completions를 제공하는 경우에는 기존처럼 `completion/complete` 요청을 프록시합니다.
- 로컬 tool/resource/prompt 정의를 추가하지 않으므로 AGENTS의 프록시 구조 규칙을 유지합니다.

## 수정 대상

- `src/proxy-server.ts`

## 검증 계획

1. `pnpm build`
2. 가능하면 `node dist/index.js`로 시작 오류가 사라졌는지 확인

## 승인 요청

위 내용대로 `src/proxy-server.ts`를 수정해도 될까요?
