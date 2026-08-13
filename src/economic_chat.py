"""Database-grounded economic reasoning chat for the dashboard."""

from __future__ import annotations

import json
import re
from datetime import date, timedelta

import httpx

from ai_analyzer import (
    DEFAULT_MODEL,
    GITHUB_MODELS_BASE_URL,
    build_provider,
    google_response_schema,
    parse_chat_completion_response,
    parse_google_response,
    parse_openai_response,
)
from config import load_settings
from macro_data import build_scenarios, macro_prompt, scenario_prompt, series_snapshot

KNOWLEDGE_CARDS = [
    ("기회비용과 한계 의사결정", "microeconomics", "선택의 경제적 비용은 지출액뿐 아니라 포기한 최선의 대안 가치다. 총액보다 추가 한 단위의 편익과 비용을 비교한다.", ["희소 자원의 대체 사용", "한계편익과 한계비용", "매몰비용 배제"], ["대안과 제약을 식별할 수 있다"], ["비가역성과 선택권 가치가 크면 단순 비교가 부족하다"], ["기회비용", "한계비용", "투자", "예산"]),
    ("통화정책 전달 경로", "monetary_economics", "정책금리는 시장금리, 신용, 자산가격, 환율과 기대를 거쳐 소비·투자·물가에 영향을 준다.", ["이자율 경로", "신용 경로", "환율 경로", "기대 경로"], ["정책 변화가 시장금리에 전달된다"], ["공급 충격과 고정금리 부채는 효과를 약화하거나 지연한다"], ["금리", "통화정책", "인플레이션", "물가", "환율", "연준", "한국은행"]),
    ("유가 충격의 한국경제 전달 경로", "open_economy", "순에너지 수입국에서 유가 상승은 수입물가와 생산비를 높이고 실질구매력과 경상수지를 압박할 수 있다.", ["교역조건 악화", "비용상승 물가", "실질소득 감소", "환율 피드백"], ["유가 상승이 지속되고 원화 수입가격이 상승한다"], ["산유국 수요, 세율 조정과 헤지가 일부 상쇄할 수 있다"], ["유가", "원유", "에너지", "호르무즈", "한국", "수입물가", "경상수지"]),
    ("환율의 물가·실물경제 전달", "open_economy", "통화가치 하락은 수입가격을 높이고 수출 경쟁력을 개선할 수 있지만 외화부채와 수입중간재 비용도 증가시킨다.", ["수입물가 전가", "순수출", "외화부채 효과", "물가 기대"], ["계약과 가격이 조정될 시간이 있다"], ["수요 둔화, 환헤지와 마진 조정은 효과를 제한한다"], ["환율", "원달러", "달러", "원화", "수입물가", "수출"]),
    ("인과추론과 경쟁 가설", "econometrics", "동행만으로 인과관계를 확정할 수 없다. 공통 원인, 역인과, 선택편향과 시차를 경쟁 가설로 검토한다.", ["교란변수", "역인과", "선택편향", "식별 전략"], ["비교 가능한 반사실을 구성할 수 있다"], ["관측자료만으로 완전한 인과 식별이 불가능할 수 있다"], ["원인", "인과", "상관관계", "효과", "영향", "가설", "반증"]),
    ("수요견인과 비용상승 인플레이션", "inflation", "물가는 총수요가 공급능력을 초과하거나 임금·원자재·환율 등 생산비가 상승할 때 오를 수 있다. 원인에 따라 정책 효과와 성장 비용이 다르다.", ["수요 갭", "원가 전가", "임금·물가 피드백", "기대 형성"], ["가격지표의 구성과 기저효과를 구분한다"], ["일시적 공급 충격과 품목별 상대가격 변화는 지속 인플레이션과 다르다"], ["물가", "인플레이션", "CPI", "생산자물가", "임금", "원자재", "기저효과"]),
    ("실질금리와 금융여건", "monetary_economics", "실질금리는 명목금리에서 기대인플레이션을 뺀 개념이며 저축·투자와 자산가치 판단에 중요하다. 금융여건은 금리뿐 아니라 신용스프레드, 환율, 주가와 대출태도를 포함한다.", ["실질 차입비용", "할인율", "신용스프레드", "위험선호"], ["기대인플레이션 측정치가 적절하다"], ["금리가 같아도 신용경색이나 위험선호 변화로 금융여건은 달라질 수 있다"], ["실질금리", "명목금리", "금융여건", "신용", "할인율", "채권", "주가"]),
    ("금리차와 자본이동·환율", "international_finance", "국가 간 기대수익률 차이는 자본이동과 환율에 영향을 주지만 환율 기대, 위험프리미엄, 헤지비용이 함께 결정한다.", ["금리차", "자본이동", "위험프리미엄", "환헤지 비용"], ["자본 이동이 가능하고 시장 접근성이 유지된다"], ["위기 시 안전자산 선호와 유동성 수요가 단순 금리차 효과를 압도할 수 있다"], ["금리차", "자본유출", "자본유입", "환율", "달러", "위험프리미엄"]),
    ("기대와 중앙은행 신뢰", "monetary_economics", "가계와 기업의 물가 기대가 임금·가격 설정에 반영되면 충격이 지속될 수 있다. 중앙은행의 일관된 목표와 소통은 기대 고정을 돕는다.", ["기대 인플레이션", "임금 협상", "가격 설정", "정책 신뢰"], ["경제주체가 정책 신호를 관찰하고 반응한다"], ["공급 제약이 장기화되면 신뢰만으로 실제 물가를 안정시키기 어렵다"], ["기대", "중앙은행", "신뢰", "포워드가이던스", "임금", "물가"]),
    ("재정정책 승수와 구축효과", "fiscal_policy", "정부지출이나 감세의 성장 효과는 경기 여유, 통화정책 반응, 수입누출과 재원조달 방식에 따라 달라진다. 완전고용에 가까우면 금리와 물가 상승으로 민간활동을 밀어낼 수 있다.", ["총수요 확대", "재정승수", "수입누출", "구축효과"], ["정책의 시점과 대상이 식별된다"], ["공급능력 확충 지출은 단기 수요효과와 장기 생산성 효과가 다르다"], ["재정정책", "정부지출", "감세", "재정승수", "국채", "부채", "경기부양"]),
    ("경상수지와 대외건전성", "open_economy", "경상수지는 무역뿐 아니라 본원소득과 이전소득을 포함하며 국내 저축과 투자의 차이와 대응한다. 적자 자체보다 조달구조, 외화유동성과 지속가능성이 중요하다.", ["저축·투자 균형", "교역조건", "대외소득", "외화유동성"], ["일시적 가격 효과와 물량 효과를 구분한다"], ["통화 약세가 곧바로 수지를 개선하지 않고 계약과 물량 조정 시차가 발생할 수 있다"], ["경상수지", "무역수지", "수출", "수입", "외환보유액", "대외부채"]),
    ("자산가격의 할인율·현금흐름 분해", "asset_pricing", "자산가격 변화는 기대 현금흐름과 할인율 변화로 나눠 볼 수 있다. 같은 뉴스도 업종별 이익 민감도, 듀레이션과 위험프리미엄에 따라 반응이 다르다.", ["기대 현금흐름", "무위험금리", "위험프리미엄", "듀레이션"], ["시장가격이 새로운 정보를 일부 반영한다"], ["단기 가격은 유동성·포지셔닝·수급 때문에 펀더멘털과 괴리될 수 있다"], ["주가", "채권", "자산가격", "할인율", "밸류에이션", "위험프리미엄", "듀레이션"]),
    ("유가 충격의 국가별 비대칭", "energy_macro", "유가 상승의 거시 효과는 국가의 에너지 순수입·순수출 구조에 따라 다르다. 순수입국은 교역조건과 실질구매력이 악화되기 쉽지만, 산유·순수출국은 에너지 소득과 투자가 늘 수 있다. 한 국가 안에서도 생산업체와 에너지 소비 가계·기업의 효과가 엇갈린다.", ["에너지 무역수지", "생산자 소득과 소비자 비용", "산업별 재분배", "물가·통화정책 피드백"], ["해당 국가의 순수입·순수출 지위와 분석 기간을 확인한다"], ["환율, 세금, 전략비축유, 헤지와 생산량 반응이 충격을 완화하거나 방향을 바꿀 수 있다"], ["유가", "원유", "에너지", "미국", "산유국", "수입국", "수출국", "석유", "인플레이션"]),
]


def seed_economic_knowledge(connection):
    sources = [
        ("internal_curated", "에미나이 Watch", "검토된 경제학 기본 원리", "", "curated_theory", 2, "GLOBAL"),
        ("bok_ecos", "한국은행", "경제통계시스템 ECOS", "https://ecos.bok.or.kr/", "official_statistics", 1, "KR"),
        ("fred", "Federal Reserve Bank of St. Louis", "FRED Economic Data", "https://fred.stlouisfed.org/", "official_statistics", 1, "US"),
        ("imf_data", "International Monetary Fund", "IMF Data", "https://www.imf.org/en/data", "international_statistics", 1, "GLOBAL"),
        ("oecd", "OECD", "OECD Economic Outlook", "https://www.oecd.org/en/topics/economic-outlook.html", "international_outlook", 1, "GLOBAL"),
    ]
    for source in sources:
        connection.execute("insert or ignore into economic_knowledge_sources (source_key,institution,title,url,source_type,trust_tier,region,verified_at) values (?,?,?,?,?,?,?,date('now'))", source)
    source_id = connection.execute("select id from economic_knowledge_sources where source_key='internal_curated'").fetchone()["id"]
    for index, card in enumerate(KNOWLEDGE_CARDS, start=1):
        title, domain, content, mechanisms, assumptions, counter, keywords = card
        connection.execute("""insert or ignore into economic_knowledge
          (knowledge_key,title,domain,content,mechanisms,assumptions,counter_conditions,keywords,source_id,confidence,status)
          values (?,?,?,?,?,?,?,?,?,0.8,'reviewed')""",
          (f"core_{index}",title,domain,content,json.dumps(mechanisms,ensure_ascii=False),json.dumps(assumptions,ensure_ascii=False),json.dumps(counter,ensure_ascii=False),json.dumps(keywords,ensure_ascii=False),source_id))


def retrieve_knowledge(connection, question, limit=4):
    terms = list(dict.fromkeys(re.findall(r"[A-Za-z0-9가-힣]{2,}", question.lower())))[:10]
    lowered_question = question.lower()
    names_korea = ("한국", "대한민국", "원화", "한국은행")
    names_other_country = ("미국", "중국", "일본", "유럽", "영국", "독일", "프랑스", "인도")
    korea_is_in_scope = any(name in lowered_question for name in names_korea)
    another_country_is_explicit = any(name in lowered_question for name in names_other_country)
    rows = connection.execute("""select k.*,s.institution,s.url as source_url from economic_knowledge k
      left join economic_knowledge_sources s on s.id=k.source_id where k.status='reviewed'""").fetchall()
    ranked = []
    for row in rows:
        item = dict(row)
        haystack = " ".join((item["title"],item["domain"],item["content"],item["keywords"])).lower()
        if another_country_is_explicit and not korea_is_in_scope and ("한국" in item["title"] or "한국" in item["content"]):
            continue
        score = sum(2 if term in item["keywords"].lower() else 1 for term in terms if term in haystack)
        ranked.append((score,item))
    ranked.sort(key=lambda pair:(pair[0],pair[1]["confidence"]),reverse=True)
    matched = [item for score,item in ranked if score>0]
    return (matched or [item for _,item in ranked])[:limit]


SYSTEM_PROMPT = """
당신은 한국어로 답하는 경제 분석 에이전트다. 제공된 대시보드 DB 근거와 경제학적 원리를 함께 사용한다.

반드시 지킬 원칙:
- 경제 결과는 하나의 원인이 아니라 수요·공급·정책·금융시장·기대·지정학 변수의 상호작용으로 형성된다고 본다.
- 질문의 핵심 변수만 분리한 기준선 분석은 허용하지만, 중요한 다른 변수가 영향을 주지 않는다고 일괄 가정하지 않는다. 기준선을 설명한 뒤 현실적인 외부 변수를 다시 결합한다.
- 주요 변수를 원인, 매개, 증폭·상쇄, 피드백 역할로 구분하고 변수 사이의 방향, 시차와 2차 효과를 밝힌다.
- 최소한 기준·우호·위험 조건을 비교하고, 어느 조건에서 결론이 약해지거나 뒤집히는지 제시한다.
- 결론보다 먼저 목표, 제약, 기회비용, 한계효과, 이해관계자의 유인, 2차 효과를 검토한다.
- 상관관계를 인과관계로 단정하지 않는다. 경쟁 가설과 결론이 바뀌는 조건을 밝힌다.
- DB 근거는 [N1] 같은 제공된 근거 번호로만 인용한다. 존재하지 않는 자료나 수치를 만들지 않는다.
- DB가 답을 직접 뒷받침하지 않으면 일반 경제 원리와 데이터 기반 판단을 명확히 구분한다.
- 투자 매수·매도 지시가 아니라 시나리오와 위험을 설명한다.
- 간결하지만 의사결정에 도움이 되게 답한다.
""".strip()


RESPONSE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "answer": {"type": "string"},
        "assumptions": {"type": "array", "items": {"type": "string"}},
        "key_variables": {"type": "array", "items": {"type": "string"}},
        "variable_interactions": {"type": "array", "items": {"type": "string"}},
        "economic_mechanisms": {"type": "array", "items": {"type": "string"}},
        "counterarguments": {"type": "array", "items": {"type": "string"}},
        "scenario_analysis": {"type": "array", "items": {"type": "string"}},
        "turning_conditions": {"type": "array", "items": {"type": "string"}},
        "uncertainty": {"type": "string"},
        "source_ids": {"type": "array", "items": {"type": "integer"}},
        "follow_ups": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "answer",
        "assumptions",
        "key_variables",
        "variable_interactions",
        "economic_mechanisms",
        "counterarguments",
        "scenario_analysis",
        "turning_conditions",
        "uncertainty",
        "source_ids",
        "follow_ups",
    ],
}


STOP_WORDS = {
    "그리고", "그러면", "하지만", "대한", "에서", "으로", "하는", "해줘", "알려줘",
    "어떻게", "무엇", "뭐야", "인가", "경제", "분석", "뉴스", "최근", "관련",
}


NON_ECONOMIC_PROBES = (
    "hi",
    "hello",
    "ping",
    "test",
    "testing",
    "ㅎㅇ",
    "안녕",
    "안녕하세요",
    "테스트",
    "하이",
)


def is_non_economic_probe(question: str) -> bool:
    normalized = re.sub(r"[^a-z0-9가-힣]+", "", str(question or "").strip().lower())
    return normalized in NON_ECONOMIC_PROBES


def question_terms(question: str) -> list[str]:
    tokens = re.findall(r"[A-Za-z0-9가-힣]{2,}", question)
    unique = []
    for token in tokens:
        normalized = token.lower()
        if normalized in STOP_WORDS or normalized in unique:
            continue
        unique.append(normalized)
    return unique[:8]


def retrieve_evidence(connection, question: str, limit: int = 10) -> list[dict]:
    terms = question_terms(question)
    params: list[object] = []
    where = "analysis_status = 'analyzed' and coalesce(user_hidden, 0) = 0"
    if terms:
        clauses = []
        for term in terms:
            clauses.append("lower(coalesce(title, '') || ' ' || coalesce(summary_ko, '') || ' ' || coalesce(analysis_ko, '') || ' ' || raw_text) like ?")
            params.append(f"%{term}%")
        where += " and (" + " or ".join(clauses) + ")"

    params.append(limit)
    rows = connection.execute(
        f"""
        select id, news_date, published_at, source_channel, telegram_message_id,
               title, summary_ko, analysis_ko, category, impact_score, risk_level
        from news_items
        where {where}
        order by impact_score desc, published_at desc
        limit ?
        """,
        params,
    ).fetchall()

    if not rows and terms:
        rows = connection.execute(
            """
            select id, news_date, published_at, source_channel, telegram_message_id,
                   title, summary_ko, analysis_ko, category, impact_score, risk_level
            from news_items
            where analysis_status = 'analyzed' and coalesce(user_hidden, 0) = 0
            order by published_at desc, impact_score desc
            limit ?
            """,
            (limit,),
        ).fetchall()

    return [dict(row) for row in rows]


def evidence_prompt(evidence: list[dict]) -> str:
    blocks = []
    for index, item in enumerate(evidence, start=1):
        blocks.append(
            "\n".join(
                [
                    f"[N{index}] DB news_id={item['id']} | {item['news_date']} | {item['source_channel']}",
                    f"제목: {item['title'] or '(제목 없음)'}",
                    f"요약: {(item['summary_ko'] or '')[:700]}",
                    f"기존 분석: {(item['analysis_ko'] or '')[:900]}",
                    f"분류/영향/위험: {item['category'] or '-'} / {item['impact_score'] or '-'} / {item['risk_level'] or '-'}",
                ]
            )
        )
    return "\n\n".join(blocks) if blocks else "관련 DB 근거 없음"


def calculate_evidence_metrics(evidence: list[dict]) -> dict:
    if not evidence:
        return {"sample_size": 0, "average_impact": None, "high_risk_share": None, "categories": {}, "period": None}
    impacts = [float(item["impact_score"]) for item in evidence if item.get("impact_score") is not None]
    high_risk = sum(1 for item in evidence if item.get("risk_level") == "높음")
    categories = {}
    dates = sorted(item["news_date"] for item in evidence if item.get("news_date"))
    for item in evidence:
        category = item.get("category") or "unknown"
        categories[category] = categories.get(category, 0) + 1
    return {
        "sample_size": len(evidence),
        "average_impact": round(sum(impacts) / len(impacts), 2) if impacts else None,
        "high_risk_share": round(high_risk / len(evidence) * 100, 1),
        "categories": dict(sorted(categories.items(), key=lambda pair: pair[1], reverse=True)),
        "period": {"start": dates[0], "end": dates[-1]} if dates else None,
    }


def metrics_prompt(metrics: dict) -> str:
    if not metrics["sample_size"]:
        return "검색 표본 없음"
    return "\n".join(
        [
            f"표본 수: {metrics['sample_size']}건",
            f"평균 영향도: {metrics['average_impact']} / 10",
            f"고위험 비중: {metrics['high_risk_share']}%",
            f"분야 분포: {json.dumps(metrics['categories'], ensure_ascii=False)}",
            f"표본 기간: {metrics['period']['start']} ~ {metrics['period']['end']}",
        ]
    )


def knowledge_prompt(knowledge: list[dict]) -> str:
    blocks = []
    for index, item in enumerate(knowledge, start=1):
        blocks.append(
            "\n".join(
                [
                    f"[K{index}] {item['title']} | 분야={item['domain']} | 신뢰도={item['confidence']}",
                    f"핵심: {item['content']}",
                    f"메커니즘: {', '.join(json.loads(item['mechanisms']))}",
                    f"가정: {', '.join(json.loads(item['assumptions']))}",
                    f"반대 조건: {', '.join(json.loads(item['counter_conditions']))}",
                    f"등록 출처: {item['institution'] or '-'} | {item['source_url'] or '-'}",
                ]
            )
        )
    return "\n\n".join(blocks) if blocks else "관련 경제 지식카드 없음"


def build_prompt(question: str, history: list[dict], evidence: list[dict], knowledge: list[dict], metrics: dict, macro: list[dict], scenarios: dict) -> str:
    conversation = []
    for message in history[-6:]:
        role = "사용자" if message.get("role") == "user" else "분석가"
        conversation.append(f"{role}: {str(message.get('content', ''))[:1200]}")
    return f"""
이전 대화:
{chr(10).join(conversation) or '(없음)'}

현재 질문:
{question}

대시보드 DB에서 검색된 근거:
{evidence_prompt(evidence)}

검토된 경제 지식카드:
{knowledge_prompt(knowledge)}

Python이 직접 계산한 검색 표본 통계:
{metrics_prompt(metrics)}

공식 거시 시계열 계산 결과:
{macro_prompt(macro)}

결정론적 시나리오 도구 결과:
{scenario_prompt(scenarios)}

표본 통계는 검색된 뉴스에 대한 기술통계이며 전체 경제나 시장을 대표한다고 확대 해석하지 마라.
거시 시계열은 각 항목의 기준일과 단위를 확인하고, 서로 다른 빈도의 지표를 단순 동시 비교하지 마라.

answer에는 먼저 한 문단으로 결론을 쓰고, 핵심 경제 메커니즘과 판단 조건을 설명하라.
assumptions에는 분석 기간, 데이터 한계, 정책 반응 등 범위와 전제를 쓰되 "다른 변수의 영향은 없다"처럼 현실의 상호작용을 지우는 포괄적 가정을 쓰지 마라.
key_variables에는 질문과 직접·간접적으로 연결된 핵심 변수 3~7개를 "변수 — 역할 — 예상 방향" 형식으로 제시하라.
variable_interactions에는 적어도 2개의 상호작용을 "변수 A × 변수 B → 전달 경로와 결과" 형식으로 제시하라. 증폭, 상쇄, 피드백과 시차를 우선 검토하라.
scenario_analysis에는 "기준:", "우호:", "위험:"으로 시작하는 세 조건을 모두 제시하고, 각 조건에서 여러 변수가 함께 어떻게 움직이는지 설명하라.
turning_conditions에는 현재 결론이 약해지거나 반대로 바뀌는 관측 가능한 조건을 제시하라.
source_ids에는 실제 사용한 근거의 번호만 넣어라. 예: N1과 N3을 썼다면 [1, 3].
follow_ups에는 분석을 개선할 후속 질문을 최대 3개 제시하라.
""".strip()


def call_provider_once(provider: dict, prompt: str) -> dict:
    if provider["provider"] == "google":
        response = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{provider['model']}:generateContent",
            params={"key": provider["api_key"]},
            json={
                "contents": [{"role": "user", "parts": [{"text": f"{SYSTEM_PROMPT}\n\n{prompt}"}]}],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "responseSchema": google_response_schema(RESPONSE_SCHEMA),
                },
            },
            timeout=45,
        )
        response.raise_for_status()
        return parse_google_response(response.json())

    if provider["provider"] == "github":
        response = provider["client"].chat.completions.create(
            model=provider["model"],
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "economic_analysis", "schema": RESPONSE_SCHEMA, "strict": True},
            },
        )
        return parse_chat_completion_response(response)

    response = provider["client"].responses.create(
        model=provider["model"],
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        text={"format": {"type": "json_schema", "name": "economic_analysis", "schema": RESPONSE_SCHEMA, "strict": True}},
    )
    return parse_openai_response(response)


def call_provider(provider: dict, prompt: str) -> tuple[dict, dict]:
    errors = []
    for candidate in [provider, *provider.get("fallbacks", [])]:
        try:
            return call_provider_once(candidate, prompt), candidate
        except Exception as error:
            errors.append(f"{candidate['provider']}:{candidate['model']} - {str(error)[:160]}")
    raise RuntimeError("모든 AI 공급자 호출에 실패했습니다: " + " | ".join(errors))


def save_analysis_record(connection, question: str, result: dict) -> int:
    cursor = connection.execute(
        """insert into economic_analyses
          (question,answer,assumptions,key_variables,variable_interactions,mechanisms,
           counterarguments,scenario_analysis,turning_conditions,uncertainty,
           knowledge_used,news_sources,calculations,macro_snapshot,scenarios,provider,model)
          values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            question,
            result.get("answer", ""),
            json.dumps(result.get("assumptions", []), ensure_ascii=False),
            json.dumps(result.get("key_variables", []), ensure_ascii=False),
            json.dumps(result.get("variable_interactions", []), ensure_ascii=False),
            json.dumps(result.get("economic_mechanisms", []), ensure_ascii=False),
            json.dumps(result.get("counterarguments", []), ensure_ascii=False),
            json.dumps(result.get("scenario_analysis", []), ensure_ascii=False),
            json.dumps(result.get("turning_conditions", []), ensure_ascii=False),
            result.get("uncertainty", ""),
            json.dumps(result.get("knowledge", []), ensure_ascii=False),
            json.dumps(result.get("sources", []), ensure_ascii=False),
            json.dumps(result.get("calculations", {}), ensure_ascii=False),
            json.dumps(result.get("macro_series", []), ensure_ascii=False),
            json.dumps(result.get("scenarios", {}), ensure_ascii=False),
            result.get("provider"),
            result.get("model"),
        ),
    )
    analysis_id = cursor.lastrowid
    score = score_analysis(result)
    connection.execute(
        """insert into economic_analysis_scores
          (analysis_id,total_score,structure_score,evidence_score,reasoning_score,calibration_score,checks)
          values (?,?,?,?,?,?,?)""",
        (
            analysis_id, score["total"], score["structure"], score["evidence"],
            score["reasoning"], score["calibration"],
            json.dumps(score["checks"], ensure_ascii=False),
        ),
    )
    if score["total"] < 80:
        failed = [name for name, passed in score["checks"].items() if not passed]
        connection.execute(
            """insert into economic_improvement_queue
              (queue_key,analysis_id,issue_type,severity,detail)
              values (?,?,?,?,?) on conflict(queue_key) do update set
              severity=excluded.severity,detail=excluded.detail,status='open',updated_at=current_timestamp""",
            (
                f"analysis:{analysis_id}:quality", analysis_id, "low_quality_score",
                "high" if score["total"] < 60 else "medium",
                f"자동 품질점수 {score['total']}점. 실패 항목: {', '.join(failed) or '없음'}",
            ),
        )
    forecast_date = date.today()
    target_date = forecast_date + timedelta(days=30)
    for indicator in result.get("scenarios", {}).get("indicators", []):
        connection.execute(
            """insert into economic_forecasts
              (analysis_id,series_id,forecast_date,target_date,favorable_value,base_value,adverse_value)
              values (?,?,?,?,?,?,?)""",
            (
                analysis_id, indicator["series_id"], forecast_date.isoformat(), target_date.isoformat(),
                indicator.get("favorable"), indicator.get("base"), indicator.get("adverse"),
            ),
        )
    connection.commit()
    return analysis_id


def score_analysis(result: dict) -> dict:
    assumptions = result.get("assumptions", [])
    key_variables = result.get("key_variables", [])
    interactions = result.get("variable_interactions", [])
    mechanisms = result.get("economic_mechanisms", [])
    counterarguments = result.get("counterarguments", [])
    scenario_analysis = result.get("scenario_analysis", [])
    turning_conditions = result.get("turning_conditions", [])
    sources = result.get("sources", [])
    knowledge = result.get("knowledge", [])
    uncertainty = result.get("uncertainty", "")
    scenario_disclaimer = result.get("scenarios", {}).get("disclaimer", "")
    checks = {
        "substantive_answer": len(result.get("answer", "")) >= 120,
        "maps_key_variables": len(key_variables) >= 3,
        "has_variable_interactions": len(interactions) >= 2,
        "multiple_mechanisms": len(mechanisms) >= 2,
        "has_counterarguments": len(counterarguments) >= 1,
        "has_scenario_analysis": len(scenario_analysis) >= 3,
        "has_turning_conditions": len(turning_conditions) >= 1,
        "has_news_evidence": len(sources) >= 1,
        "has_knowledge": len(knowledge) >= 1,
        "states_scope_assumptions": len(assumptions) >= 2,
        "states_uncertainty": len(uncertainty) >= 20,
        "scenario_is_calibrated": bool(scenario_disclaimer),
    }
    structure = (10 if checks["substantive_answer"] else 0) + (7.5 if checks["maps_key_variables"] else 0) + (7.5 if checks["multiple_mechanisms"] else 0)
    evidence_score = (15 if checks["has_news_evidence"] else 0) + (10 if checks["has_knowledge"] else 0)
    reasoning = (
        (7.5 if checks["has_counterarguments"] else 0)
        + (10 if checks["has_variable_interactions"] else 0)
        + (7.5 if checks["has_scenario_analysis"] else 0)
        + (5 if checks["has_turning_conditions"] else 0)
    )
    calibration = (
        (10 if checks["states_uncertainty"] else 0)
        + (5 if checks["scenario_is_calibrated"] else 0)
        + (5 if checks["states_scope_assumptions"] else 0)
    )
    return {
        "total": round(structure + evidence_score + reasoning + calibration, 1),
        "structure": structure,
        "evidence": evidence_score,
        "reasoning": reasoning,
        "calibration": calibration,
        "checks": checks,
    }


def answer_economic_question(connection, question: str, history: list[dict] | None = None) -> dict:
    cleaned = " ".join(question.split())
    if not cleaned:
        raise ValueError("질문을 입력해 주세요.")
    if len(cleaned) > 2000:
        raise ValueError("질문은 2,000자 이내로 입력해 주세요.")
    if is_non_economic_probe(cleaned):
        return {
            "answer": "안녕하세요. 저는 경제 분석 전용 AI입니다. 금리, 물가, 고용, 환율, 주식·채권·원자재 또는 지정학적 변수의 경제 영향을 질문해 주세요.",
            "assumptions": [],
            "key_variables": [],
            "variable_interactions": [],
            "economic_mechanisms": [],
            "counterarguments": [],
            "scenario_analysis": [],
            "turning_conditions": [],
            "uncertainty": "",
            "sources": [],
            "knowledge": [],
            "calculations": {},
            "macro_series": [],
            "scenarios": {},
            "provider": "system",
            "model": "intent-router",
            "analysis_id": None,
        }

    safe_history = [item for item in (history or []) if item.get("role") in {"user", "assistant"}]
    evidence = retrieve_evidence(connection, cleaned)
    seed_economic_knowledge(connection)
    connection.commit()
    knowledge = retrieve_knowledge(connection, cleaned)
    metrics = calculate_evidence_metrics(evidence)
    macro = series_snapshot(connection, cleaned)
    scenarios = build_scenarios(macro, metrics)
    settings = load_settings()
    provider = build_provider(settings, DEFAULT_MODEL)
    result, used_provider = call_provider(provider, build_prompt(cleaned, safe_history, evidence, knowledge, metrics, macro, scenarios))

    used = []
    seen_source_numbers = set()
    for source_number in result.get("source_ids", []):
        if isinstance(source_number, int) and source_number not in seen_source_numbers and 1 <= source_number <= len(evidence):
            seen_source_numbers.add(source_number)
            item = evidence[source_number - 1]
            used.append(
                {
                    "ref": f"N{source_number}",
                    "id": item["id"],
                    "title": item["title"] or "제목 없음",
                    "date": item["news_date"],
                    "source": item["source_channel"],
                    "url": f"https://t.me/{item['source_channel']}/{item['telegram_message_id']}",
                }
            )

    result["sources"] = used
    result["knowledge"] = [
        {
            "title": item["title"],
            "domain": item["domain"],
            "institution": item["institution"],
            "url": item["source_url"],
            "confidence": item["confidence"],
        }
        for item in knowledge
    ]
    result["calculations"] = metrics
    result["macro_series"] = macro
    result["scenarios"] = scenarios
    result["provider"] = used_provider["provider"]
    result["model"] = used_provider["model"]
    result.pop("source_ids", None)
    result["analysis_id"] = save_analysis_record(connection, cleaned, result)
    return result
