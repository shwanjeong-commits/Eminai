# Eminai n8n / Appsmith 운영 연동

## 1. 설계 원칙

Eminai의 Telegram 수집기, 분류기, deduplication, 분석 큐, AI worker, SQLite transaction, retry/backoff, 알림 파이프라인은 그대로 유지한다. n8n은 외부 trigger·운영 자동화·외부 알림 orchestration을 담당하고, Appsmith는 운영자 Control Center를 담당한다. 기존 사용자용 Eminai 웹앱은 사용자 뉴스·시장·분석 인터페이스로 계속 사용한다.

> **중요:** n8n과 Appsmith는 SQLite를 직접 변경하지 않는다. 모든 변경은 Eminai HTTP API를 통해 수행한다.

이번 변경에서는 기존 API의 브라우저 session cookie와 same-origin 정책을 약화시키지 않기 위해 `/api/ops/*`에만 별도 machine-to-machine 인증을 추가했다. 실제 키는 runtime `.env` 또는 secret manager에만 두고 Git에는 두지 않는다.

## 2. 역할 분리

| 영역 | Eminai Python | n8n | Appsmith | 기존 사용자 웹앱 |
| --- | --- | --- | --- | --- |
| Telegram 실시간 수집 | 담당 | 사용하지 않음 | 조회 | 표시하지 않음 |
| 분류·dedup·분석 queue | 담당 | 사용하지 않음 | 조회 | 결과 표시 |
| AI 분석·재시도 | 담당 | 사용하지 않음 | 상태 조회 | 결과 표시 |
| 운영 자동화·외부 연동 | API 제공 | 담당 | 사용하지 않음 | 사용하지 않음 |
| 운영자 수동 명령 | API 제공 | orchestration 가능 | 버튼 제공 | 기존 기능 유지 |
| 사용자 뉴스 경험 | 데이터 제공 | 사용하지 않음 | 사용하지 않음 | 담당 |

n8n/Appsmith를 적용하지 않은 이유는 기존 수집·분석 파이프라인을 재구현하면 single-writer invariant와 retry/backoff가 중복되고, 데이터 경합과 운영 복잡성만 증가하기 때문이다. 기존 Eminai가 이미 제공하는 Telegram/Web Push alert도 중복 구현하지 않는다.

## 3. 인증

각 요청은 다음 header를 사용한다.

```http
X-Eminai-Ops-Key: <runtime secret>
```

Eminai는 `EMINAI_OPS_API_KEY`가 비어 있거나 요청 키가 일치하지 않으면 `401`을 반환한다. 비교는 constant-time 비교를 사용한다. 브라우저용 `eminai_auth` cookie, same-origin 검사, 기존 API 인증은 변경하지 않는다. CORS를 전체 허용하지 않으며, 응답에는 기존 보안 header가 적용된다.

```bash
export EMINAI_BASE_URL="http://127.0.0.1:4173"
export EMINAI_OPS_API_KEY="configure-this-outside-git"
```

실제 secret은 shell history, 문서, workflow export, Git에 남기지 않는다.

## 4. Ops API

| Method | Endpoint | 목적 | 성공 응답 |
| --- | --- | --- | --- |
| GET | `/api/ops/status` | collector, worker, queue, failed/deferred, analyzed, automation 상태 | `200` JSON |
| GET | `/api/ops/news` | 운영 queue/news 조회 | `200` JSON |
| POST | `/api/ops/manual-update` | 기존 manual update를 queue에 등록 | `200` JSON |
| POST | `/api/ops/reanalyze` | 기존 분석 row를 다시 `queued`로 변경 | `200` JSON |

### 4.1 상태 조회

```bash
curl -sS "$EMINAI_BASE_URL/api/ops/status" \
  -H "X-Eminai-Ops-Key: $EMINAI_OPS_API_KEY"
```

응답에는 `collector`, `analysisWorker`, `manualUpdate`, `filterAudit`, `automationStatus`, `analysis`, `queueEstimate`, `aiStatus`, `filterAuditStatus`가 포함된다. `queueEstimate`는 기존 `build_analysis_stats()`를 재사용하며, worker가 quota-deferred 또는 failed인 경우 조건부 ETA로 표시된다.

### 4.2 뉴스·queue 조회

지원 query parameter는 `status`, `limit`, `offset`, `min_priority`, `content_type`이다. `limit`은 1–200, `offset`은 0 이상이어야 한다.

```bash
curl -sS "$EMINAI_BASE_URL/api/ops/news?status=queued&limit=50&offset=0" \
  -H "X-Eminai-Ops-Key: $EMINAI_OPS_API_KEY"
```

각 item에는 `id`, `sourceChannel`, `publishedAt`, `title`, `rawText`, `analysisStatus`, `analysisPriority`, `analysisReason`, `impactScore`, `sentiment`, `riskLevel`, `category`, `contentType`, `hidden`, `updatedAt`가 포함된다. 원문은 운영 화면에 필요한 범위로만 잘라 반환한다.

### 4.3 Manual update

```bash
curl -sS -X POST "$EMINAI_BASE_URL/api/ops/manual-update" \
  -H "X-Eminai-Ops-Key: $EMINAI_OPS_API_KEY"
```

이 endpoint는 새 Telegram collection 코드를 실행하지 않는다. 기존 `start_manual_update()`를 호출해 `manual_update` 상태를 `queued`로 만들고, 실제 수집은 기존 `live_collector`가 처리한다.

### 4.4 Reanalysis

```bash
curl -sS -X POST "$EMINAI_BASE_URL/api/ops/reanalyze" \
  -H "Content-Type: application/json" \
  -H "X-Eminai-Ops-Key: $EMINAI_OPS_API_KEY" \
  -d '{"id":123}'
```

기존 `/api/news/action`의 reanalyze와 같은 공통 함수가 summary·analysis·impact·sentiment·risk·category를 지우고 `analysis_status='queued'`로 변경한다. 새 AI 요청은 이 endpoint가 직접 실행하지 않으며 기존 `analysis_worker`가 처리한다. 존재하지 않는 id는 `404`다.

## 5. n8n workflow 설계

### A. `eminai-health-monitor`

노드 순서는 **Schedule Trigger(5분) → HTTP Request → Code/IF 평가 → 알림 대상 분기 → Telegram/Email/Webhook 알림**이다. HTTP Request는 `GET $EMINAI_BASE_URL/api/ops/status`를 호출하고 `X-Eminai-Ops-Key` credential header를 사용한다. `analysis.queued`, `analysis.failed`, `analysis.deferred`, collector status, worker status, `automationStatus[].errorCount`를 평가한다. collector가 `listening`이 아니거나 worker가 `failed/deferred`이거나 queue가 운영 기준을 넘을 때만 알림을 보낸다. HTTP 401/429/5xx는 별도 실패 branch로 보내고, API key를 메시지에 포함하지 않는다.

### B. `eminai-manual-update`

노드 순서는 **Webhook 또는 Manual Trigger → HTTP Request**다. HTTP Request는 `POST $EMINAI_BASE_URL/api/ops/manual-update`이고 JSON body는 없다. `200`이며 `ok=true`이고 `status=queued`이면 성공으로 간주한다. `401`은 credential 오류, `429`는 잠시 후 재시도, `5xx`는 운영 장애로 분류한다.

### C. `eminai-reanalyze`

노드 순서는 **Webhook/Input → 입력 검증 → HTTP Request → 결과 반환**이다. 입력 `id`가 양의 정수인지 먼저 검증한다. HTTP Request는 `POST $EMINAI_BASE_URL/api/ops/reanalyze`, `Content-Type: application/json`, body `{ "id": {{$json.id}} }`를 사용한다. `200`과 `status=queued`를 성공으로, `404`를 없는 뉴스, `400`을 입력 오류, `401/429/5xx`를 운영 오류로 분류한다.

### D. `eminai-daily-ops-report`

노드 순서는 **Schedule Trigger(하루 1회) → status 조회 → news 통계 조회 → 요약 Code node → Telegram/Email**이다. status에서 collected/analyzed/queued/failed/deferred와 high-impact queue를 조합한다. report에는 raw secret, 전체 원문, stack trace를 넣지 않는다. 이미 Eminai가 보내는 자체 Telegram/Web Push alert와 중복되지 않도록 외부 수신자용 일일 운영 요약으로 한정한다.

n8n에 저장할 credential은 `X-Eminai-Ops-Key`라는 HTTP Header Auth credential로 만들고, workflow export JSON에는 실제 credential 값이 포함되지 않도록 한다.

## 6. Appsmith 운영자 Console

Appsmith에는 `Eminai Ops REST` datasource를 만들고 base URL을 Eminai 서버 주소로 설정한다. 공통 header로 `X-Eminai-Ops-Key`를 추가하되, 값은 Appsmith secret/credential 저장소에 둔다. DB datasource는 만들지 않는다.

| 화면 | 데이터 source | 주요 표시·동작 |
| --- | --- | --- |
| Operations | `GET /api/ops/status` | collector, worker, queue, failed/deferred, last analyzed, automation status; `POST /api/ops/manual-update` 버튼 |
| Analysis Queue | `GET /api/ops/news?status=queued...` | id, source, published time, status, priority, reason, impact/risk/category; row action으로 reanalyze |
| News QA | `GET /api/ops/news?limit=...` 및 기존 상세 API | raw text, summary, analysis, impact, sentiment, risk, category; 기존 상세/reanalysis API 재사용 |

Operations 화면의 새로고침은 status API를 호출한다. Analysis Queue의 페이지네이션은 `limit`과 `offset`을 사용한다. Re-analyze 버튼은 `POST /api/ops/reanalyze`를 호출한 뒤 queue query를 다시 실행한다. Appsmith query에 API key를 text widget이나 페이지에 노출하지 않는다.

## 7. 오류 처리와 보안 점검

`401`은 키 누락·불일치, `400`은 JSON/parameter 오류, `404`는 없는 endpoint 또는 news id, `413`은 body size 초과, `429`는 rate limit, `5xx`는 서버 장애로 해석한다. Ops endpoint에도 기존 JSON body 제한과 rate limit이 적용된다. 오류 응답에는 secret이나 stack trace를 반환하지 않는다.

기존 브라우저 endpoint는 cookie authentication과 same-origin 정책을 계속 사용한다. Ops endpoint는 machine key만으로 동작하지만, 해당 경로만 별도 분기되며 기존 `/api/*` 인증 정책을 대체하지 않는다. 운영 환경에서는 HTTPS reverse proxy와 secret manager를 사용하고, IP-only HTTP 환경에서는 key가 전송 중 노출될 수 있으므로 외부 공개 전에 HTTPS를 적용한다.

## 8. 백업·마이그레이션

이번 변경은 SQLite schema migration을 추가하지 않는다. 배포 전 기존 `news.db`와 runtime `.env`를 각각 백업한다. `.env`는 파일 권한 `600`을 유지하고, DB는 live news/analysis 데이터를 포함하므로 전체 DB를 외부 도구가 직접 교체하지 않는다. Ops API key를 교체할 때는 n8n credential과 Appsmith secret을 먼저 준비한 뒤 runtime 환경을 갱신하고 서비스를 재시작한다.

## 9. 문제 해결

`401`이면 서버 runtime에 `EMINAI_OPS_API_KEY`가 실제로 설정되어 있는지, header 이름과 공백이 올바른지 확인한다. `/api/ops/status`의 collector가 `listening`이 아니면 Telegram collector 로그와 DB의 `automation_status`를 확인한다. queue가 증가하지만 collector가 정상이라면 `analysisWorker`의 status/detail 및 provider quota를 확인한다. `POST /api/ops/manual-update`가 `queued`를 반환해도 즉시 분석 완료를 의미하지 않으며, 실제 처리는 기존 collector와 analysis worker의 비동기 경계에서 진행된다.

## 10. 운영 평가

이번 통합의 실질적 개선점은 운영자가 DB에 직접 접근하지 않고 queue·worker·manual update·reanalysis를 일관된 API로 제어할 수 있게 된 점이다. 반대로 n8n이나 Appsmith로 수집·분석을 옮기지 않았으므로 도구 도입 자체로 인한 중복 파이프라인이나 운영 복잡성은 추가하지 않았다. hide/exclude/deep-analysis/failed requeue는 기존 API의 공통화 범위와 변경 위험을 조사한 뒤 후속 backlog로 남길 수 있다.
