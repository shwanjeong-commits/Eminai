# Eminai 밀린 뉴스 일괄 분석 지시문

첨부한 `eminai_chatgpt_backlog.json`의 모든 `items`를 경제·시장·지정학 전문 분석가 관점에서 분석하세요.

중요 규칙:

1. 입력의 `id`와 `telegram_message_id`를 정확히 유지하세요.
2. 모든 입력 항목에 대해 결과를 정확히 하나씩 만드세요. 생략하거나 합치지 마세요.
3. 원문에서 확인되는 사실과 추론을 구분하고, 확인되지 않은 주장·일정·의견을 확정 사실처럼 쓰지 마세요.
4. 투자 권유를 하지 마세요.
5. 결과는 한국어로 작성하세요.
6. 마크다운 설명이나 코드 펜스를 넣지 말고, UTF-8 JSON 파일 내용만 출력하세요.

출력 최상위 형식:

```json
{
  "format": "eminai-chatgpt-analysis-v1",
  "analyses": []
}
```

각 `analyses` 항목은 아래 필드를 모두 포함해야 합니다.

```json
{
  "id": 123,
  "telegram_message_id": 456,
  "title": "짧고 명확한 한국어 제목",
  "summary_ko": "확인된 사실만 담은 2문장 요약",
  "analysis_ko": "변화의 의미, 경제·시장·외교 전달 경로를 설명하는 3~5문장 분석",
  "drivers": ["핵심 동인 1", "핵심 동인 2"],
  "transmission_channels": ["전달 경로 1", "전달 경로 2"],
  "watch_points": ["확인할 후속 신호 1", "확인할 후속 신호 2"],
  "uncertainty_ko": "해석을 바꿀 수 있는 불확실성 1문장",
  "impact_score": 0,
  "sentiment": "중립",
  "risk_level": "중간",
  "category": "markets"
}
```

허용값:

- `impact_score`: 0~10 숫자
- `sentiment`: `긍정`, `부정`, `혼재`, `중립` 중 하나
- `risk_level`: `낮음`, `중간`, `높음` 중 하나
- `category`: `macro`, `geopolitics`, `markets`, `energy` 중 하나

점수 기준:

- 0~2: 일상적 정보, 파급효과 제한
- 3~4: 관련성은 있으나 범위가 좁거나 기존 흐름 확인
- 5~6: 산업·지역·정책에 의미 있는 신호
- 7~8: 여러 시장으로 번질 수 있는 큰 변화·긴장 고조·중앙은행 충격
- 9~10: 시스템 충격, 세계적 공급 차질, 대규모 군사·정책 충격

완료된 결과를 `eminai_chatgpt_results.json`이라는 파일로 제공하세요.
