const state = {
  view: "home",
  lang: localStorage.getItem("eminai_lang") || "ko",
  authRequired: false,
  authenticated: false,
  authError: "",
  authExpiresAt: null,
  authExpiryTimer: null,
  payload: {
    dailyBriefings: {},
    newsItems: [],
    issues: [],
    assetViews: [],
    regionViews: [],
    aiStatus: {},
    analysisStats: {},
    economicEvaluation: {},
    calendarEvents: [],
    sourceDocuments: [],
    meta: {},
  },
  selectedNewsId: null,
  selectedDate: "",
  selectedRegion: "",
  selectedAsset: "",
  assetHubFilter: "all",
  assetHubSearch: "",
  watchlist: (() => { try { return JSON.parse(localStorage.getItem("eminai_watchlist") || "[]"); } catch { return []; } })(),
  newsHubQuery: "",
  newsHubSource: "all",
  newsHubImpact: "all",
  newsHubRegion: "all",
  newsHubTopic: "all",
  newsHubSort: "latest",
  newsHubDate: "all",
  marketAssets: [],
  marketIndicators: [],
  marketIndicatorMeta: {},
  marketIndicatorsLoading: false,
  marketIndicatorsError: "",
  indicatorCategoryFilter: "all",
  selectedMacroGauge: null,
  marketData: null,
  selectedMarketSymbol: "^GSPC",
  selectedCalendarEventId: null,
  calendarMonth: "2026-07",
  calendarMode: "week",
  calendarWeekOffset: 0,
  calendarCountry: "all",
  calendarCategory: "all",
  calendarImportance: "all",
  marketAssetFilter: "all",
  marketRange: "6mo",
  marketInterval: "1d",
  marketLoading: false,
  marketError: "",
  marketRequestId: 0,
  marketChartViewport: null,
  chatMessages: [],
  chatLoading: false,
  deepAnalysisById: {},
  deepAnalysisLoadingId: null,
  deepAnalysisError: "",
  translationsById: {},
  translationLoading: false,
  translationError: "",
};

const els = {
  nav: document.querySelector("#nav"),
  pageTitle: document.querySelector("#pageTitle"),
  pageStatus: document.querySelector("#pageStatus"),
  content: document.querySelector("#content"),
  detail: document.querySelector("#detail"),
  lastUpdatedAt: document.querySelector("#lastUpdatedAt"),
  manualUpdateStatus: document.querySelector("#manualUpdateStatus"),
  manualUpdateButton: document.querySelector("#manualUpdateButton"),
  languageToggle: document.querySelector("#languageToggle"),
  brandTitle: document.querySelector("#brandTitle"),
  brandSubtitle: document.querySelector("#brandSubtitle"),
  updateBoxLabel: document.querySelector("#updateBoxLabel"),
  sideQueued: document.querySelector("#sideQueued"),
  sideRegion: document.querySelector("#sideRegion"),
};

const viewMeta = {
  home: ["에미나이 Watch", "세계정세 자동 분석 AI"],
  dashboard: ["세계정세 리스크 상황판", "지역별 위험과 핵심 뉴스를 한 화면에서 확인"],
  daily: ["일일 뉴스 분석", "날짜별 뉴스, 원문, AI 요약을 빠르게 확인"],
  flows: ["이슈 흐름", "과거 뉴스와 현재 뉴스를 연결해서 추적"],
  regions: ["지역 리스크", "지역별 위험 신호와 관련 뉴스를 확인"],
  assets: ["종목/자산 영향", "뉴스가 자산군에 미치는 영향을 분류"],
  market: ["종목 차트", "지수·ETF·주식·암호화폐·원자재의 가격 흐름을 확인"],
  indicators: ["경제지표", "거시경제·금리·물가·위험 지표의 현재 상태와 판정 기준을 확인"],
  calendar: ["주요 경제 일정", "일정을 클릭해 실제치·컨센서스·이전치와 공식 출처를 확인"],
  chat: ["경제 분석 챗봇", "데이터베이스 근거와 경제적 사고로 질문을 분석"],
  evaluation: ["경제 분석 평가", "답변 품질, 사용자 평가와 예측 성과를 추적"],
  ai: ["AI 분석 현황", "수집기, 분석기, 필터 감사 상태 점검"],
};

const I18N = {
  ko: {
    brand: "에미나이 Watch",
    subtitle: "세계정세 자동 분석 AI",
    englishToggle: "English Ver",
    updateLabel: "최신 업데이트",
    refresh: "새로고침",
    updating: "업데이트 중",
    waiting: "대기 중",
    nav: {
      home: "메인",
      dashboard: "상황판",
      daily: "일일 뉴스",
      flows: "이슈 흐름",
      regions: "지역 리스크",
      assets: "종목/자산",
      market: "차트",
      indicators: "경제지표",
      calendar: "주요 일정",
      chat: "경제 챗봇",
      evaluation: "분석 평가",
      ai: "AI 분석 현황",
    },
    viewMeta: {
      home: ["에미나이 Watch", "세계정세 자동 분석 AI"],
      dashboard: ["세계정세 리스크 상황판", "지역별 위험과 핵심 뉴스를 한 화면에서 확인"],
      daily: ["일일 뉴스 분석", "날짜별 뉴스, 원문, AI 요약을 빠르게 확인"],
      flows: ["이슈 흐름", "과거 뉴스와 현재 뉴스를 연결해서 추적"],
      regions: ["지역 리스크", "지역별 위험 신호와 관련 뉴스를 확인"],
      assets: ["종목/자산 영향", "뉴스가 자산군에 미치는 영향을 분류"],
      market: ["종목 차트", "지수·ETF·주식·암호화폐·원자재 가격 흐름 확인"],
      indicators: ["경제지표", "거시경제·금리·물가·위험 지표의 현재 상태 확인"],
      calendar: ["주요 경제 일정", "일정 클릭 시 실제치·예상치와 공식 출처 확인"],
      chat: ["경제 분석 챗봇", "데이터베이스 근거와 경제 사고로 질문 분석"],
      evaluation: ["경제 분석 평가", "답변 점수, 사용자 평가, 예측 성과 추적"],
      ai: ["AI 분석 현황", "수집기, 분석기, 필터 감사 상태 점검"],
    },
    detail: {
      emptyTitle: "상세 패널",
      emptyText: "뉴스를 선택하면 원문과 AI 분석을 표시합니다.",
      summary: "AI 요약",
      analysis: "AI 분석",
      impactInfo: "영향 정보",
      impact: "영향도",
      risk: "위험도",
      region: "지역",
      original: "원문 보기",
      telegram: "텔레그램 원문 열기",
      pendingSummary: "요약 대기 중입니다.",
      pendingAnalysis: "분석 대기 중입니다.",
    },
    deep: {
      title: "투자자 추가분석",
      generate: "추가분석",
      refresh: "다시분석",
      loading: "투자자용 추가분석 생성 중...",
      empty: "원인-결과 흐름, 수혜/피해 가능성, 숫자 체크포인트는 버튼을 누르면 생성됩니다.",
      noItems: "아직 표시할 항목이 없습니다.",
      cause: "원인",
      action: "행위/사건",
      directResult: "직접 결과",
      secondOrder: "2차 영향",
      affectedAssets: "직접 영향 자산",
      beneficiaries: "수혜 가능성",
      hurtParties: "피해 가능성",
      shortTerm: "단기",
      mediumTerm: "중기",
      longTerm: "장기",
      pricedIn: "가격 반영 여부",
      indicators: "숫자로 확인할 지표",
      counter: "반대 시나리오",
      confirmation: "확정성",
      unclear: "불명확",
    },
    score: {
      market: "시장 영향도",
      geopolitics: "지정학 위험도",
      persistence: "지속성",
      spread: "확산 가능성",
    },
  },
  en: {
    brand: "Eminai Watch",
    subtitle: "Automated Geopolitical Intelligence AI",
    englishToggle: "한국어 Ver",
    updateLabel: "Latest Update",
    refresh: "Refresh",
    updating: "Updating",
    waiting: "Idle",
    nav: {
      home: "Home",
      dashboard: "Situation",
      daily: "Daily News",
      flows: "Issue Flows",
      regions: "Region Risks",
      assets: "Assets",
      market: "Charts",
      indicators: "Indicators",
      calendar: "Calendar",
      chat: "Economy Chat",
      evaluation: "Evaluation",
      ai: "AI Status",
    },
    viewMeta: {
      home: ["Eminai Watch", "Automated Geopolitical Intelligence AI"],
      dashboard: ["Global Risk Board", "Track regional risk and key news on one screen"],
      daily: ["Daily News Analysis", "Review news, originals, and AI summaries by date"],
      flows: ["Issue Flows", "Connect past and current news into storylines"],
      regions: ["Region Risks", "Check regional risk signals and related news"],
      assets: ["Asset Impact", "Classify how news may affect asset groups"],
      market: ["Market Charts", "Track indices, ETFs, stocks, crypto, and commodities"],
      indicators: ["Economic Indicators", "Read macro, rate, inflation, and risk indicators"],
      calendar: ["Key Economic Calendar", "Review actuals, forecasts, and official sources"],
      chat: ["Economic Analysis Chat", "Ask questions grounded in the news database"],
      evaluation: ["Analysis Evaluation", "Track answer scores, feedback, and forecast results"],
      ai: ["AI Analysis Status", "Monitor collectors, analyzers, and filter audits"],
    },
    detail: {
      emptyTitle: "Detail Panel",
      emptyText: "Select a news item to view original text and AI analysis.",
      summary: "AI Summary",
      analysis: "AI Analysis",
      impactInfo: "Impact Info",
      impact: "Impact",
      risk: "Risk",
      region: "Region",
      original: "Original Text",
      telegram: "Open Telegram Source",
      pendingSummary: "Summary pending.",
      pendingAnalysis: "Analysis pending.",
    },
    deep: {
      title: "Investor Deep Dive",
      generate: "Deep Dive",
      refresh: "Regenerate",
      loading: "Generating investor deep dive...",
      empty: "Click the button to generate causal flow, winner/loser map, and numeric watch points.",
      noItems: "No items to display yet.",
      cause: "Cause",
      action: "Action/Event",
      directResult: "Direct Result",
      secondOrder: "Second-order Effects",
      affectedAssets: "Affected Assets",
      beneficiaries: "Potential Beneficiaries",
      hurtParties: "Potential Losers",
      shortTerm: "Short Term",
      mediumTerm: "Medium Term",
      longTerm: "Long Term",
      pricedIn: "Priced-in Assessment",
      indicators: "Numeric Indicators",
      counter: "Counter Scenarios",
      confirmation: "Confirmation",
      unclear: "Unclear",
    },
    score: {
      market: "Market Impact",
      geopolitics: "Geopolitical Risk",
      persistence: "Persistence",
      spread: "Spillover Potential",
    },
  },
};

function t(path) {
  return path.split(".").reduce((value, key) => value?.[key], I18N[state.lang]) ?? path;
}

function localizedViewMeta() {
  if (state.lang === "ko") return {
    home: ["Eminai Watch", "미국·한국 시장을 한 화면에서 추적하는 경제 인텔리전스"],
    dashboard: ["시장 상황", "핵심 위험과 시장 신호를 종합해서 확인합니다"],
    daily: ["뉴스·근거", "수집 뉴스와 공식 자료를 함께 검색하고 비교합니다"],
    flows: ["이슈 흐름", "주요 이슈가 시간에 따라 어떻게 전개되는지 추적합니다"],
    regions: ["지역 리스크", "국가와 지역별 위험 신호를 비교합니다"],
    assets: ["자산 허브", "종목·지수·ETF와 연결된 뉴스와 일정을 확인합니다"],
    watchlist: ["관심 자산", "저장한 자산의 뉴스·차트·일정을 빠르게 확인합니다"],
    market: ["시장 차트", "주요 지수·ETF·주식·환율·원자재 가격을 확인합니다"],
    indicators: ["경제지표", "거시경제·금리·물가·고용 지표의 현재 상태를 확인합니다"],
    calendar: ["경제 캘린더", "발표 일정과 실제치·예상치·이전치를 확인합니다"],
    chat: ["경제 AI", "대시보드의 뉴스와 지표를 근거로 질문합니다"],
    evaluation: ["분석 평가", "AI 분석의 정확성과 사용자 평가를 추적합니다"],
    ai: ["시스템 현황", "뉴스 수집과 AI 분석 자동화 상태를 확인합니다"],
  };
  return {
    ...I18N[state.lang].viewMeta,
    watchlist: state.lang === "en"
      ? ["Watchlist", "Review saved assets, related news, and upcoming events"]
      : ["관심 자산", "저장한 종목·지수·ETF의 뉴스와 일정을 한곳에서 확인"],
  };
}

function localizeRisk(value) {
  if (state.lang !== "en") return value;
  return { "높음": "High", "중간": "Medium", "낮음": "Low" }[value] || value;
}

function localizeRegion(value) {
  if (state.lang !== "en") return value;
  return {
    "미국": "United States",
    "중국": "China",
    "중동": "Middle East",
    "유럽": "Europe",
    "러시아·우크라이나": "Russia-Ukraine",
    "한국": "South Korea",
    "글로벌": "Global",
  }[value] || value;
}

const UI_TEXT_EN = {
  "에미나이 Watch": "Eminai Watch",
  "에미나이": "Eminai",
  "세계정세 자동 분석 AI": "Automated Geopolitical Intelligence AI",
  "텔레그램 경제·해외정세 뉴스를 실시간으로 수집하고, 지역 리스크와 자산 영향을 연결해서 보여주는 자동 분석 상황실입니다.": "A live intelligence dashboard that collects Telegram economy and geopolitical news, then connects regional risks with asset impact.",
  "실시간 수집": "Live Collection",
  "분석 대기": "Analysis Queue",
  "고위험 뉴스": "High-risk News",
  "현재 핵심": "Current Focus",
  "AI 현재 상황 판단": "AI Current Judgment",
  "현재 판정": "Current Judgment",
  "시장 영향도": "Market Impact",
  "지정학 위험도": "Geopolitical Risk",
  "지속성": "Persistence",
  "확산 가능성": "Spillover Potential",
  "지금 먼저 볼 뉴스": "Priority News",
  "오늘의 판단": "Today's Judgment",
  "위험 상승": "Risk Rising",
  "관찰": "Watch",
  "핵심 지역": "Key Region",
  "민감 자산": "Sensitive Asset",
  "최신 업데이트": "Latest Update",
  "지역별 위험 신호": "Regional Risk Signals",
  "최근 데이터 기준": "Based on Latest Data",
  "고위험 뉴스": "High-risk News",
  "최상위 지역": "Top Region",
  "총 뉴스": "Total News",
  "주의": "Watch",
  "처리 중": "Processing",
  "정상": "Normal",
  "수집": "Collected",
  "수집 뉴스": "Collected News",
  "평균 영향도": "Average Impact",
  "최고 위험": "Highest Risk",
  "날짜": "Date",
  "전체": "All",
  "지정학": "Geopolitics",
  "시장": "Markets",
  "공급망": "Supply Chain",
  "중동": "Middle East",
  "중국": "China",
  "금리": "Rates",
  "진행 중인 이슈 타임라인": "Active Issue Timeline",
  "표시할 뉴스가 없습니다.": "No news to display.",
  "흐름 요약": "Flow Summary",
  "지역 리스크": "Region Risk",
  "자산 영향": "Asset Impact",
  "자산별 민감도": "Asset Sensitivity",
  "원자재": "Commodities",
  "주식": "Equities",
  "환율": "FX",
  "자산 영향 데이터가 없습니다.": "No asset impact data yet.",
  "차트 종목": "Chart Watchlist",
  "종목 목록을 불러오는 중입니다.": "Loading asset list.",
  "시장 차트": "Market Chart",
  "경제지표 읽는 법": "How to Read Indicators",
  "현재 경제 체온": "Current Economic Pulse",
  "경제지표 상태판": "Economic Indicator Board",
  "분석 완료": "Analyzed",
  "판정 이유": "Judgment Reasons",
  "뉴스 필터 개선 상태": "News Filter Improvement",
  "자동화 상태": "Automation Status",
  "실시간": "Realtime",
  "누적": "Cumulative",
  "자동화 상태 데이터가 없습니다.": "No automation status data.",
  "자동화 해석": "Automation Reading",
  "누적 분석": "Total Analyses",
  "평균 품질점수": "Average Quality Score",
  "도움됨 비율": "Helpful Rate",
  "평가 완료 예측": "Evaluated Forecasts",
  "자동 품질 채점": "Automated Quality Scoring",
  "30일 결과 검증": "30-day Outcome Audit",
  "평가 대기": "Pending Evaluation",
  "평균 기준 오차": "Average Base Error",
  "반복 약점": "Repeated Weaknesses",
  "개선 대기 항목": "Improvement Queue",
  "최근 경제 분석": "Recent Economic Analyses",
  "최근 10건": "Latest 10",
  "평가 기준": "Evaluation Criteria",
  "일정 상세": "Calendar Detail",
  "경제적 사고 프레임": "Economic Reasoning Frame",
  "연결 대기": "Waiting for Connection",
  "AI 상황 판단": "AI Situation Judgment",
  "관찰 포인트": "Watch Points",
  "상황판": "Situation",
  "일일 뉴스": "Daily News",
  "이슈 흐름": "Issue Flows",
  "종목/자산": "Assets",
  "종목 차트": "Market Charts",
  "경제지표": "Indicators",
  "AI 분석 현황": "AI Status",
  "지역 리스크 맵과 핵심 뉴스를 한 화면에서 확인합니다.": "View the regional risk map and key news on one screen.",
  "날짜별 뉴스, 원문, AI 요약을 빠르게 훑습니다.": "Quickly scan news, original text, and AI summaries by date.",
  "과거 뉴스와 현재 뉴스를 연결해 사건의 방향을 봅니다.": "Connect past and current news to understand how events are evolving.",
  "미국, 중국, 중동, 한국 등 지역별 위험을 비교합니다.": "Compare risks across the U.S., China, the Middle East, South Korea, and more.",
  "원유, 달러, 반도체 같은 자산군 영향도를 봅니다.": "Review impact across assets such as oil, the dollar, and semiconductors.",
  "지수·ETF·주식·비트코인·원자재의 가격 흐름을 봅니다.": "Track price trends across indices, ETFs, stocks, Bitcoin, and commodities.",
  "물가·금리·변동성·유동성 지표와 상태 기준을 봅니다.": "Monitor inflation, rates, volatility, liquidity, and status thresholds.",
  "수집기, 분석기, 필터 감사가 정상인지 점검합니다.": "Check whether collectors, analyzers, and filter audits are healthy.",
  "글로벌": "Global",
  "러시아·우크라이나": "Russia-Ukraine",
  "미국 국채·장기금리": "U.S. Treasuries / Long-term Rates",
  "원유·에너지": "Oil / Energy",
  "호르무즈·원유": "Hormuz / Oil",
  "미국·이란 긴장": "U.S.-Iran Tensions",
  "중국 무역·기술": "China Trade / Technology",
  "미국 금리·달러": "U.S. Rates / Dollar",
  "AI·반도체": "AI / Semiconductors",
};

function ui(value) {
  if (state.lang !== "en") return value;
  const text = String(value ?? "");
  return UI_TEXT_EN[text] || localizeRegion(localizeRisk(text));
}

function formatCount(value) {
  return state.lang === "en" ? `${num(value)} items` : `${num(value)}건`;
}

function translateStaticText(text) {
  if (state.lang !== "en") return text;
  const trimmed = text.trim();
  if (!trimmed) return text;
  if (/^\d+건$/.test(trimmed)) {
    return text.replace(trimmed, `${trimmed.replace("건", "")} items`);
  }
  if (/^\d+점$/.test(trimmed)) {
    return text.replace(trimmed, `${trimmed.replace("점", "")} pts`);
  }
  const translated = UI_TEXT_EN[trimmed] || localizeRisk(trimmed);
  return translated !== trimmed ? text.replace(trimmed, translated) : text;
}

function applyEnglishStaticText(root = document.body) {
  if (state.lang !== "en" || !root) return;
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  const nodes = [];
  while (walker.nextNode()) nodes.push(walker.currentNode);
  nodes.forEach((node) => {
    node.nodeValue = translateStaticText(node.nodeValue);
  });
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function safeExternalUrl(value) {
  try {
    const parsed = new URL(String(value || ""));
    return ["http:", "https:"].includes(parsed.protocol) ? parsed.href : "#";
  } catch {
    return "#";
  }
}

function compact(value, limit = 110) {
  const text = String(value || "").replace(/\s+/g, " ").trim();
  if (!text) return state.lang === "en" ? "Summary pending." : "요약 대기 중입니다.";
  return text.length > limit ? `${text.slice(0, limit - 1)}...` : text;
}

function num(value, digits = 0) {
  const number = Number(value || 0);
  return digits ? number.toFixed(digits) : number.toLocaleString();
}

function telegramDailyLink() {
  const url = String(state.payload.meta?.telegramDailyChannelUrl || "").trim();
  if (!url) return "";
  const label = state.lang === "en" ? "Get Daily News on Telegram" : "텔레그램으로 데일리 뉴스 받아보기";
  const note = state.lang === "en"
    ? "Receive the daily report cards at 08:00 and 18:00 KST."
    : "매일 08:00, 18:00 KST 카드뉴스와 일일 보고를 받아봅니다.";
  return `<a class="telegram-daily-link" href="${escapeHtml(safeExternalUrl(url))}" target="_blank" rel="noopener noreferrer">
    <span>${escapeHtml(label)}</span>
    <small>${escapeHtml(note)}</small>
  </a>`;
}

function impactTone(score) {
  if (Number(score || 0) >= 8) return "high";
  if (Number(score || 0) >= 6) return "mid";
  return "low";
}

function riskTone(risk) {
  if (risk === "높음") return "risk-high";
  if (risk === "중간") return "risk-watch";
  return "risk-low";
}

function latestNews() {
  return [...state.payload.newsItems].sort((a, b) => String(b.publishedAt || "").localeCompare(String(a.publishedAt || "")));
}

function highImpactNews(limit = 4) {
  return [...state.payload.newsItems]
    .sort((a, b) => Number(b.impact || 0) - Number(a.impact || 0))
    .slice(0, limit);
}

function selectedNews() {
  return state.payload.newsItems.find((item) => item.id === state.selectedNewsId) || highImpactNews(1)[0] || latestNews()[0];
}

function dateList() {
  return [...new Set(state.payload.newsItems.map((item) => item.date).filter(Boolean))].sort().reverse();
}

function currentDate() {
  const dates = dateList();
  if (!state.selectedDate || !dates.includes(state.selectedDate)) state.selectedDate = dates[0] || "";
  return state.selectedDate;
}

function newsForDate(date) {
  return state.payload.newsItems.filter((item) => item.date === date);
}

function visibleNewsForCurrentView() {
  if (state.view === "daily") return newsForDate(currentDate()).slice(0, 20);
  if (state.view === "dashboard") return highImpactNews(12);
  if (state.view === "home") return highImpactNews(8);
  return latestNews().slice(0, 12);
}

function ensureEnglishTranslations() {
  if (state.lang !== "en" || state.translationLoading) return;
  const ids = visibleNewsForCurrentView()
    .map((item) => item.id)
    .filter((id) => id && !state.translationsById[id]);
  if (!ids.length) return;
  requestEnglishTranslations(ids.slice(0, 12));
}

function topRegionName() {
  const region = [...state.payload.regionViews].sort((a, b) => Number(b.pressure || 0) - Number(a.pressure || 0))[0];
  return region?.region || latestNews()[0]?.region || "-";
}

function queuedCount() {
  const target = state.payload.aiStatus?.byScope?.analysis_target || {};
  return Number(target.queued || 0);
}

function formatQueueDuration(minutes) {
  if (minutes === null || minutes === undefined || !Number.isFinite(Number(minutes))) return state.lang === "en" ? "Unavailable" : "계산 대기";
  const value = Math.max(0, Math.round(Number(minutes)));
  if (value < 60) return state.lang === "en" ? `${value} min` : `${value}분`;
  if (value < 1440) {
    const hours = Math.floor(value / 60);
    const mins = value % 60;
    return state.lang === "en" ? `${hours}h${mins ? ` ${mins}m` : ""}` : `${hours}시간${mins ? ` ${mins}분` : ""}`;
  }
  const days = Math.floor(value / 1440);
  const hours = Math.round((value % 1440) / 60);
  return state.lang === "en" ? `${days}d${hours ? ` ${hours}h` : ""}` : `${days}일${hours ? ` ${hours}시간` : ""}`;
}

function formatQueueResumeTime(value) {
  if (!value) return null;
  const normalized = typeof value === "string" && /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(value)
    ? `${value.replace(" ", "T")}Z`
    : value;
  const date = new Date(normalized);
  if (Number.isNaN(date.getTime())) return null;
  return new Intl.DateTimeFormat(state.lang === "en" ? "en-US" : "ko-KR", {
    timeZone: "Asia/Seoul",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function queueEstimateView() {
  const estimate = state.payload.analysisStats?.queueEstimate || {};
  const remaining = Number(estimate.retryRemainingMinutes);
  const hasResumeEstimate = estimate.retryRemainingMinutes !== null && estimate.retryRemainingMinutes !== undefined && Number.isFinite(remaining);
  const resumeAt = formatQueueResumeTime(estimate.retryAt);
  const resumeLabel = !estimate.conditional
    ? (state.lang === "en" ? "Running" : "처리 중")
    : resumeAt
      ? (state.lang === "en" ? `After ${resumeAt}` : `${resumeAt} 이후`)
      : !hasResumeEstimate
        ? (state.lang === "en" ? "Availability unknown" : "가능 시간 확인 중")
        : remaining <= 0
          ? (state.lang === "en" ? "Available now" : "현재 재개 가능")
          : (state.lang === "en" ? `Available in about ${formatQueueDuration(remaining)}` : `약 ${formatQueueDuration(remaining)} 후 가능`);
  if (!Number(estimate.queued || 0)) return { label: state.lang === "en" ? "Complete" : "처리 완료", note: state.lang === "en" ? "No queued items" : "분석 대기 항목이 없습니다", resumeLabel: state.lang === "en" ? "Not needed" : "필요 없음", tone:"risk-low" };
  if (estimate.etaMinutes === null || estimate.etaMinutes === undefined) return { label: state.lang === "en" ? "Calculating" : "계산 대기", note: state.lang === "en" ? "Not enough recent throughput data" : "최근 처리 속도 데이터가 부족합니다", resumeLabel, tone:"risk-watch" };
  const range = `${formatQueueDuration(estimate.lowerMinutes)}~${formatQueueDuration(estimate.upperMinutes)}`;
  const speed = state.lang === "en" ? `${num(estimate.ratePerHour, 1)}/hour` : `시간당 ${num(estimate.ratePerHour, 1)}건`;
  if (estimate.conditional) return { label: state.lang === "en" ? `After resume: ${range}` : `재개 후 ${range}`, note: state.lang === "en" ? `Provider limited · recent speed ${speed}` : `API 할당량 제한 중 · 최근 속도 ${speed}`, resumeLabel, tone:"risk-watch" };
  return { label: range, note: state.lang === "en" ? `Estimated from recent speed ${speed}` : `최근 실제 처리 속도 ${speed} 기준`, resumeLabel, tone:"risk-low" };
}

function averageImpact(items) {
  if (!items.length) return 0;
  const total = items.reduce((sum, item) => sum + Number(item.impact || 0), 0);
  return total / items.length;
}

function topAssetName() {
  return state.payload.assetViews[0]?.name || "-";
}

function buildHomeJudgment() {
  const situation = state.payload.situation;
  if (situation) {
    const topWatch = (situation.topWatch || [])
      .map((watch) => state.payload.newsItems.find((item) => item.id === watch.id) || watch);
    const dimensionScores = situation.dimensionScores || {};
    const highRiskCount = state.payload.newsItems.filter((item) => item.risk === "높음" || Number(item.impact || 0) >= 8).length;
    const englishSummary = `As of the latest update, Eminai is tracking ${formatCount(state.payload.newsItems.length)} with ${formatCount(highRiskCount)} flagged as high-impact or high-risk. Market impact is ${num(dimensionScores.market?.score || 0, 1)}, geopolitical risk is ${num(dimensionScores.geopolitics?.score || 0, 1)}, persistence is ${num(dimensionScores.persistence?.score || 0, 1)}, and spillover potential is ${num(dimensionScores.spread?.score || 0, 1)}.`;
    return {
      level: state.lang === "en" ? ui(situation.level || "관찰") : situation.level || "관찰",
      tone: situation.tone || "risk-watch",
      summary: state.lang === "en" ? englishSummary : situation.summary || "상황 판단 데이터가 준비 중입니다.",
      metrics: [
        { label: "시장 영향도", value: `${num(dimensionScores.market?.score || 0, 1)}`, tone: impactTone(dimensionScores.market?.score || 0) },
        { label: "지정학 위험도", value: `${num(dimensionScores.geopolitics?.score || 0, 1)}`, tone: impactTone(dimensionScores.geopolitics?.score || 0) },
        { label: "지속성", value: `${num(dimensionScores.persistence?.score || 0, 1)}`, tone: impactTone(dimensionScores.persistence?.score || 0) },
        { label: "확산 가능성", value: `${num(dimensionScores.spread?.score || 0, 1)}`, tone: impactTone(dimensionScores.spread?.score || 0) },
      ],
      reasons: state.lang === "en" ? [] : situation.reasons || [],
      changes: situation.changes || [],
      keyVariables: situation.keyVariables || [],
      watch: topWatch.length ? topWatch : highImpactNews(3),
    };
  }

  const news = latestNews().slice(0, 80);
  const highImpact = news.filter((item) => item.risk === "높음" || Number(item.impact || 0) >= 8);
  const topRegion = [...state.payload.regionViews].sort((a, b) => Number(b.pressure || 0) - Number(a.pressure || 0))[0];
  const topAsset = state.payload.assetViews[0];
  const briefing = state.payload.dailyBriefings[currentDate()] || {};
  const avgImpact = averageImpact(news);
  const regionPressure = Number(topRegion?.pressure || 0);
  const queued = queuedCount();
  let level = "안정 관찰";
  let tone = "risk-low";

  if (highImpact.length >= 8 || regionPressure >= 82) {
    level = "위험 상승";
    tone = "risk-high";
  } else if (highImpact.length >= 3 || avgImpact >= 6.4 || regionPressure >= 65 || queued > 0) {
    level = "주의";
    tone = "risk-watch";
  }

  const summary = briefing.summary
    ? compact(briefing.summary, 220)
    : `${topRegion?.region || "주요 지역"} 쪽 압력과 ${topAsset?.name || "민감 자산"} 반응을 중심으로 최근 뉴스 ${num(news.length)}건을 관찰 중입니다.`;

  return {
    level,
    tone,
    summary,
    metrics: [
      { label: "핵심 지역", value: topRegion?.region || topRegionName(), tone: regionPressure >= 75 ? "risk-high" : "risk-watch" },
      { label: "민감 자산", value: topAsset?.name || "-", tone: "blue" },
      { label: "고영향 뉴스", value: `${num(highImpact.length)}건`, tone: highImpact.length ? "risk-high" : "risk-low" },
      { label: "분석 대기", value: `${num(queued)}건`, tone: queued ? "risk-watch" : "risk-low" },
    ],
    reasons: [],
    changes: [],
    keyVariables: [],
    watch: highImpactNews(3),
  };
}

function homeJudgmentPanel() {
  const judgment = buildHomeJudgment();
  const watch = judgment.watch.length
    ? judgment.watch.map((rawItem) => {
      const item = translatedItem(rawItem);
      return `
      <button class="watch-item" data-view="daily" data-news-id="${item.id}">
        <span class="watch-score">${num(item.impact || 0)}</span>
        <span>${escapeHtml(item.title || (state.lang === "en" ? "Untitled" : "제목 없음"))}</span>
        <strong>${escapeHtml(localizeRegion(item.region || "글로벌"))}</strong>
      </button>
    `;
    }).join("")
    : `<div class="watch-empty">${state.lang === "en" ? "No high-impact news candidates at the moment." : "현재 고영향 뉴스 후보가 없습니다."}</div>`;

  return `
    <section class="panel judgment-panel">
      <div class="judgment-main">
        <div>
          <div class="eyebrow">AI CURRENT JUDGMENT</div>
          <h3>${escapeHtml(ui("AI 현재 상황 판단"))}</h3>
          <p>${escapeHtml(judgment.summary)}</p>
        </div>
        <div class="judgment-badge ${judgment.tone}">
          <span>${escapeHtml(ui("현재 판정"))}</span>
          <strong>${escapeHtml(judgment.level)}</strong>
        </div>
      </div>
      <div class="judgment-grid">
        ${judgment.metrics.map((item) => smallCard(item.label, escapeHtml(item.value), item.tone)).join("")}
      </div>
      ${judgment.keyVariables?.length ? `
        <div class="variable-row">
          ${judgment.keyVariables.map((item) => `<span><strong>${escapeHtml(item.name)}</strong>${num(item.score, 1)}</span>`).join("")}
        </div>
      ` : ""}
      ${judgment.reasons?.length ? `
        <div class="reason-list">
          ${judgment.reasons.slice(0, 3).map((item) => `<p>${escapeHtml(item)}</p>`).join("")}
        </div>
      ` : ""}
      <div class="watch-list">
        <div class="watch-title">${escapeHtml(ui("지금 먼저 볼 뉴스"))}</div>
        ${watch}
      </div>
    </section>
  `;
}

function formatUpdateTime(value) {
  if (!value) return "-";
  const text = String(value).trim();
  const normalized = /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(text)
    ? `${text.replace(" ", "T")}Z`
    : text;
  const date = new Date(normalized);
  if (Number.isNaN(date.getTime())) return String(value);
  const options = state.lang === "en"
    ? { timeZone: "Asia/Seoul", month: "short", day: "2-digit", hour: "numeric", minute: "2-digit" }
    : { timeZone: "Asia/Seoul", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" };
  return new Intl.DateTimeFormat(state.lang === "en" ? "en-US" : "ko-KR", options).format(date);
}

function menuCard(view, title, summary, icon) {
  return `
    <button class="menu-card" type="button" data-go="${view}">
      <div>
        <div class="menu-card-top">
          <h2>${escapeHtml(ui(title))}</h2>
          <span class="menu-icon">${icon}</span>
        </div>
        <p>${escapeHtml(ui(summary))}</p>
      </div>
      <span class="open-label">${state.lang === "en" ? "Open" : "열기"}</span>
    </button>
  `;
}

function smallCard(label, value, tone = "") {
  return `<div class="card"><label>${escapeHtml(ui(label))}</label><strong class="${tone}">${escapeHtml(ui(value))}</strong></div>`;
}

function metric(label, value, note, tone = "") {
  return `<div class="metric"><div><label>${escapeHtml(ui(label))}</label><b>${escapeHtml(ui(value))}</b></div><span class="${tone}">${escapeHtml(ui(note))}</span></div>`;
}

function tagList(tags = []) {
  return tags.slice(0, 4).map((tag) => `<span class="chip">${escapeHtml(tag)}</span>`).join("");
}

function translatedItem(item) {
  if (state.lang !== "en") return item;
  const translation = state.translationsById[item?.id];
  if (!translation) return item;
  return {
    ...item,
    title: translation.title || item.title,
    summary: translation.summary || item.summary,
    analysis: translation.analysis || item.analysis,
    rawText: translation.rawText || item.rawText,
    tags: translation.tags?.length ? translation.tags : item.tags,
    translated: true,
  };
}

function translationHint(item) {
  if (state.lang !== "en" || !item || item.translated) return "";
  if (state.translationLoading) return `<p class="muted translation-note">Translating this news item into English...</p>`;
  if (state.translationError) return `<p class="deep-error translation-note">${escapeHtml(state.translationError)}</p>`;
  return `<p class="muted translation-note">English translation is queued. Korean source text is shown until it is ready.</p>`;
}

function scoreBreakdownRows(item) {
  const breakdown = item?.scoreBreakdown || {};
  const rows = ["market", "geopolitics", "persistence", "spread"]
    .map((key) => ({ key, ...breakdown[key] }))
    .filter((score) => score.score != null);
  if (!rows.length) return "";
  return `
    <div class="score-breakdown">
      ${rows.map((score) => `
        <div>
          <span>${escapeHtml(t(`score.${score.key}`) || score.label)}</span>
          <strong class="${impactTone(score.score)}">${num(score.score, 1)}</strong>
        </div>
      `).join("")}
    </div>
  `;
}

function listItems(items = []) {
  return items.length
    ? `<ul>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`
    : `<p class="muted">${escapeHtml(t("deep.noItems"))}</p>`;
}

function renderDeepAnalysis(newsId) {
  const analysis = state.deepAnalysisById[newsId];
  if (state.deepAnalysisLoadingId === newsId) {
    return `<div class="deep-loading">${escapeHtml(t("deep.loading"))}</div>`;
  }
  if (state.deepAnalysisError) {
    return `<p class="deep-error">${escapeHtml(state.deepAnalysisError)}</p>`;
  }
  if (!analysis) {
    return `<p class="muted">${escapeHtml(t("deep.empty"))}</p>`;
  }

  const chain = analysis.causeEffectChain || {};
  const horizon = analysis.timeHorizon || {};
  return `
    <div class="deep-analysis">
      <p>${escapeHtml(analysis.investorSummary || "")}</p>
      <div class="chain-grid">
        <div><span>${escapeHtml(t("deep.cause"))}</span><strong>${escapeHtml(chain.cause || "-")}</strong></div>
        <div><span>${escapeHtml(t("deep.action"))}</span><strong>${escapeHtml(chain.action || "-")}</strong></div>
        <div><span>${escapeHtml(t("deep.directResult"))}</span><strong>${escapeHtml(chain.direct_result || "-")}</strong></div>
      </div>
      <div class="deep-block"><b>${escapeHtml(t("deep.secondOrder"))}</b>${listItems(chain.second_order_effects || [])}</div>
      <div class="deep-block"><b>${escapeHtml(t("deep.affectedAssets"))}</b>${listItems(analysis.affectedAssets || [])}</div>
      <div class="deep-split">
        <div><b>${escapeHtml(t("deep.beneficiaries"))}</b>${listItems(analysis.beneficiaries || [])}</div>
        <div><b>${escapeHtml(t("deep.hurtParties"))}</b>${listItems(analysis.hurtParties || [])}</div>
      </div>
      <div class="horizon-grid">
        <div><span>${escapeHtml(t("deep.shortTerm"))}</span><p>${escapeHtml(horizon.short_term || "-")}</p></div>
        <div><span>${escapeHtml(t("deep.mediumTerm"))}</span><p>${escapeHtml(horizon.medium_term || "-")}</p></div>
        <div><span>${escapeHtml(t("deep.longTerm"))}</span><p>${escapeHtml(horizon.long_term || "-")}</p></div>
      </div>
      <div class="deep-block"><b>${escapeHtml(t("deep.pricedIn"))}</b><p>${escapeHtml(analysis.pricedInAssessment || "-")}</p></div>
      <div class="deep-block"><b>${escapeHtml(t("deep.indicators"))}</b>${listItems(analysis.numericIndicators || [])}</div>
      <div class="deep-block"><b>${escapeHtml(t("deep.counter"))}</b>${listItems(analysis.counterScenarios || [])}</div>
      <div class="deep-block"><b>${escapeHtml(t("deep.confirmation"))}: ${escapeHtml(analysis.confirmationLevel || t("deep.unclear"))}</b>${listItems(analysis.checklist || [])}</div>
    </div>
  `;
}

function deepAnalysisSection(item) {
  return `
    <div class="detail-section">
      <div class="detail-title">${escapeHtml(t("deep.title"))}</div>
      <div class="detail-actions">
        <button class="analysis-action" type="button" data-deep-analysis-id="${item.id}">${escapeHtml(t("deep.generate"))}</button>
        ${state.deepAnalysisById[item.id] ? `<button class="analysis-action secondary" type="button" data-deep-analysis-id="${item.id}" data-refresh-deep="1">${escapeHtml(t("deep.refresh"))}</button>` : ""}
      </div>
      ${renderDeepAnalysis(item.id)}
    </div>
  `;
}

function newsRow(item) {
  item = translatedItem(item);
  const score = Number(item.impact || 0).toFixed(0);
  return `
    <button class="news" type="button" data-news-id="${item.id}">
      <span class="impact ${impactTone(item.impact)}">${score}</span>
      <span class="news-main">
        <strong>${escapeHtml(item.title)}</strong>
        <em>${escapeHtml(compact(item.summary || item.rawText, 120))}</em>
        <span class="chips">${tagList(item.tags || [])}</span>
      </span>
      <span class="time">${escapeHtml(item.time || "")}</span>
    </button>
  `;
}

function newsFeed(title, items, tabs = ["전체", "지정학", "시장", "공급망"]) {
  const rows = items.length ? items.map(newsRow).join("") : `<p class="empty">${escapeHtml(ui("표시할 뉴스가 없습니다."))}</p>`;
  return `
    <section class="panel">
      <div class="feed-head">
        <h2>${escapeHtml(ui(title))}</h2>
        <div class="tabs">${tabs.map((tab, index) => `<span class="${index === 0 ? "active" : ""}">${escapeHtml(ui(tab))}</span>`).join("")}</div>
      </div>
      <div class="news-list">${rows}</div>
    </section>
  `;
}

function detailForNews(item) {
  if (!item) {
    return `<h2>${escapeHtml(t("detail.emptyTitle"))}</h2><p class="empty">${escapeHtml(t("detail.emptyText"))}</p>`;
  }
  item = translatedItem(item);
  return `
    <h2>${escapeHtml(item.title)}</h2>
    ${translationHint(item)}
    <div class="detail-section">
      <div class="detail-title">${escapeHtml(t("detail.summary"))}</div>
      <p>${escapeHtml(item.summary || t("detail.pendingSummary"))}</p>
    </div>
    <div class="detail-section">
      <div class="detail-title">${escapeHtml(t("detail.analysis"))}</div>
      <p>${escapeHtml(item.analysis || t("detail.pendingAnalysis"))}</p>
    </div>
    <div class="detail-section">
      <div class="detail-title">${escapeHtml(t("detail.impactInfo"))}</div>
      <div class="risk-row"><span>${escapeHtml(t("detail.impact"))}</span><strong class="${impactTone(item.impact)}">${Number(item.impact || 0).toFixed(1)}</strong></div>
      <div class="risk-row"><span>${escapeHtml(t("detail.risk"))}</span><strong class="${riskTone(item.risk)}">${escapeHtml(localizeRisk(item.risk || "-"))}</strong></div>
      <div class="risk-row"><span>${escapeHtml(t("detail.region"))}</span><strong>${escapeHtml(localizeRegion(item.region || "-"))}</strong></div>
      ${scoreBreakdownRows(item)}
    </div>
    ${deepAnalysisSection(item)}
    <details class="detail-section original">
      <summary>${escapeHtml(t("detail.original"))}</summary>
      <p>${escapeHtml(item.rawText || "")}</p>
    </details>
    ${item.sourceUrl ? `<a class="source-link" href="${escapeHtml(safeExternalUrl(item.sourceUrl))}" target="_blank" rel="noopener noreferrer">${escapeHtml(t("detail.telegram"))}</a>` : ""}
  `;
}

function renderHome() {
  const news = state.payload.newsItems;
  const highRisk = news.filter((item) => item.risk === "높음" || Number(item.impact || 0) >= 8).length;
  const latest = state.payload.meta?.latestNewsAt || state.payload.meta?.lastUpdatedAt;
  const queueEta = queueEstimateView();
  const topRegion = topRegionName();
  const topAsset = topAssetName();
  els.content.innerHTML = `
    <section class="panel hero">
      <div class="hero-copy">
        <div class="hero-kicker">GEOPOLITICAL MARKET INTELLIGENCE</div>
        <h2 class="hero-title">에미나이 <span>Watch</span></h2>
        <p>텔레그램 경제·해외정세 뉴스를 실시간으로 수집하고, 지역 리스크와 자산 영향을 연결해서 보여주는 자동 분석 상황실입니다.</p>
      </div>
      <div class="hero-signal">
        <div class="signal-row"><span>실시간 수집</span><strong class="risk-low">ON</strong></div>
        <div class="signal-row"><span>분석 대기</span><strong>${num(queuedCount())}건</strong></div>
        <div class="signal-row"><span>고위험 뉴스</span><strong class="risk-high">${num(highRisk)}건</strong></div>
        <div class="signal-row"><span>현재 핵심</span><strong class="risk-watch">${escapeHtml(topRegion)}</strong></div>
      </div>
    </section>
    ${homeJudgmentPanel()}
    <section class="menu-grid">
      ${menuCard("dashboard", "상황판", "지역 리스크 맵과 핵심 뉴스를 한 화면에서 확인합니다.", "M")}
      ${menuCard("daily", "일일 뉴스", "날짜별 뉴스, 원문, AI 요약을 빠르게 훑습니다.", "D")}
      ${menuCard("flows", "이슈 흐름", "과거 뉴스와 현재 뉴스를 연결해 사건의 방향을 봅니다.", "F")}
      ${menuCard("regions", "지역 리스크", "미국, 중국, 중동, 한국 등 지역별 위험을 비교합니다.", "R")}
      ${menuCard("assets", "종목/자산", "원유, 달러, 반도체 같은 자산군 영향도를 봅니다.", "A")}
      ${menuCard("market", "종목 차트", "지수·ETF·주식·비트코인·원자재의 가격 흐름을 봅니다.", "C")}
      ${menuCard("indicators", "경제지표", "물가·금리·변동성·유동성 지표와 상태 기준을 봅니다.", "I")}
      ${menuCard("ai", "AI 분석 현황", "수집기, 분석기, 필터 감사가 정상인지 점검합니다.", "AI")}
    </section>
    <section class="home-strip">
      ${smallCard("오늘의 판단", highRisk ? "위험 상승" : "관찰", highRisk ? "risk-high" : "blue")}
      ${smallCard("핵심 지역", escapeHtml(topRegion))}
      ${smallCard("민감 자산", escapeHtml(topAsset))}
      ${smallCard("최신 업데이트", formatUpdateTime(latest), "blue")}
    </section>
  `;
  els.detail.innerHTML = detailBlock("에미나이 간판", "홈은 각 기능으로 들어가는 관문이자 현재 자동화 상태를 보여주는 간판입니다.");
}

function renderHomeV2() {
  const news = latestNews().slice(0, 8);
  const highImpact = [...news].sort((a, b) => Number(b.impact || 0) - Number(a.impact || 0));
  const regions = [...(state.payload.regionViews || [])].sort((a, b) => Number(b.pressure || 0) - Number(a.pressure || 0));
  const assets = (state.payload.assetViews || []).slice(0, 6);
  const queueEta = queueEstimateView();
  const now = new Date();
  const upcoming = (state.payload.calendarEvents || [])
    .filter((item) => new Date(item.scheduledAt || item.scheduled_at || item.date || 0) >= new Date(now.getFullYear(), now.getMonth(), now.getDate()))
    .sort((a, b) => new Date(a.scheduledAt || a.scheduled_at || a.date || 0) - new Date(b.scheduledAt || b.scheduled_at || b.date || 0))
    .slice(0, 5);
  const leadingRegion = regions[0];
  const riskCount = state.payload.newsItems.filter((item) => Number(item.impact || 0) >= 8).length;
  const latest = state.payload.meta?.lastUpdatedAt || state.payload.meta?.latestNewsAt;

  const marketCards = assets.length
    ? assets.map((item) => `
      <button type="button" class="home-market-card" data-go="assets">
        <span>${escapeHtml(item.name || item.asset || "자산")}</span>
        <strong>${escapeHtml(item.status || item.signal || item.risk || "관찰")}</strong>
        <small>${escapeHtml(compact(item.summary || item.analysis || "관련 뉴스와 가격 흐름을 확인하세요.", 54))}</small>
      </button>`).join("")
    : `<p class="empty">표시할 시장 데이터가 없습니다.</p>`;

  const calendarRows = upcoming.length
    ? upcoming.map((item) => {
      const date = new Date(item.scheduledAt || item.scheduled_at || item.date);
      const dateLabel = Number.isNaN(date.getTime()) ? "예정" : new Intl.DateTimeFormat("ko-KR", { timeZone: "Asia/Seoul", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" }).format(date);
      return `<button type="button" class="home-calendar-row" data-go="calendar">
        <time>${escapeHtml(dateLabel)}</time>
        <span><b>${escapeHtml(item.title || "주요 일정")}</b><small>${escapeHtml(item.country || "")} · ${escapeHtml(calendarCategoryLabels[item.category] || item.category || "일정")}</small></span>
        <em class="${item.importance === "high" ? "risk-high" : "risk-watch"}">${item.importance === "high" ? "중요" : "보통"}</em>
      </button>`;
    }).join("")
    : `<p class="empty">등록된 예정 일정이 없습니다.</p>`;

  const newsRows = news.length
    ? news.map((rawItem, index) => {
      const item = translatedItem(rawItem);
      return `<button type="button" class="home-news-row" data-view="daily" data-news-id="${item.id}">
        <span class="home-news-rank">${index + 1}</span>
        <span><b>${escapeHtml(item.title || "제목 없음")}</b><small>${escapeHtml(compact(item.summary || item.rawText || "", 92))}</small></span>
        <em class="${impactTone(item.impact)}">${num(item.impact || 0)}</em>
      </button>`;
    }).join("")
    : `<p class="empty">수집된 최신 뉴스가 없습니다.</p>`;

  els.content.innerHTML = `
    <section class="home-overview">
      <div class="panel home-brief-card">
        <div class="home-section-head"><div><span>MARKET BRIEF</span><h2>오늘의 시장 한눈에 보기</h2></div><button type="button" data-go="dashboard">전체 상황판</button></div>
        <div class="home-brief-main">
          <div>
            <span class="home-status-pill ${riskCount ? "watch" : "stable"}">${riskCount ? "변동성 주의" : "시장 관찰"}</span>
            <h3>${escapeHtml(leadingRegion?.region ? `${localizeRegion(leadingRegion.region)} 이슈를 우선 확인하세요` : "수집된 시장 신호를 점검하세요")}</h3>
            <p>${escapeHtml(compact(leadingRegion?.summary || highImpact[0]?.summary || "한국과 미국의 경제 뉴스, 주요 일정, 자산 흐름을 함께 추적하고 있습니다.", 180))}</p>
          </div>
          <dl class="home-brief-stats">
            <div><dt>고영향 뉴스</dt><dd class="${riskCount ? "risk-high" : "risk-low"}">${num(riskCount)}건</dd></div>
            <div><dt>분석 대기</dt><dd>${num(queuedCount())}건</dd></div>
            <div><dt>대기열 예상</dt><dd class="${queueEta.tone}">${escapeHtml(queueEta.label)}</dd></div>
            <div><dt>재개 가능 시간</dt><dd class="${queueEta.tone}">${escapeHtml(queueEta.resumeLabel)}</dd></div>
            <div><dt>최종 갱신</dt><dd>${escapeHtml(formatUpdateTime(latest))}</dd></div>
          </dl>
        </div>
        ${telegramDailyLink()}
      </div>
      <aside class="panel home-upcoming">
        <div class="home-section-head"><div><span>NEXT EVENTS</span><h2>다가오는 주요 일정</h2></div><button type="button" data-go="calendar">캘린더</button></div>
        <div>${calendarRows}</div>
      </aside>
    </section>

    <section class="panel home-market-section">
      <div class="home-section-head"><div><span>MARKET PULSE</span><h2>주요 자산과 시장 신호</h2></div><button type="button" data-go="market">차트 보기</button></div>
      <div class="home-market-grid">${marketCards}</div>
    </section>

    <section class="home-news-layout">
      <section class="panel home-news-section">
        <div class="home-section-head"><div><span>LIVE NEWS</span><h2>지금 확인할 뉴스</h2></div><button type="button" data-go="daily">전체 뉴스</button></div>
        <div class="home-news-list">${newsRows}</div>
      </section>
      <aside class="panel home-ai-card">
        <span>AI VIEW</span>
        <h2>무엇을 먼저 봐야 하나요?</h2>
        <ol>
          ${highImpact.slice(0, 3).map((item) => `<li>${escapeHtml(compact(item.title || item.summary || "핵심 뉴스", 62))}</li>`).join("") || "<li>현재 핵심 신호를 분석하고 있습니다.</li>"}
        </ol>
        <button type="button" data-go="ai">AI 분석 열기</button>
      </aside>
    </section>
  `;
  els.detail.innerHTML = news.length ? detailForNews(news[0]) : detailBlock("시장 브리핑", "뉴스와 시장 데이터가 수집되면 상세 분석이 표시됩니다.");
}

function renderDashboard() {
  const regions = [...state.payload.regionViews].sort((a, b) => Number(b.pressure || 0) - Number(a.pressure || 0));
  const top = regions[0];
  const news = highImpactNews(5);
  els.content.innerHTML = `
    <section class="section-grid">
      <div class="panel map-panel">
        <div class="map-grid"></div>
        <div class="map-title"><span>지역별 위험 신호</span><span>최근 데이터 기준</span></div>
        ${regionNode(regions[0], "r-me")}
        ${regionNode(regions[1], "r-cn")}
        ${regionNode(regions[2], "r-us")}
        ${regionNode(regions[3], "r-ru")}
        ${regionNode(regions[4], "r-kr")}
        ${regionNode(regions[5], "r-eu")}
      </div>
      <aside class="panel panel-pad metrics">
        ${metric("고위험 뉴스", num(state.payload.newsItems.filter((item) => Number(item.impact || 0) >= 8).length), "주의", "risk-high")}
        ${metric("최상위 지역", escapeHtml(top?.region || "-"), top?.risk || "-", riskTone(top?.risk))}
        ${metric("분석 대기", `${num(queuedCount())}건`, queuedCount() ? "처리 중" : "정상", queuedCount() ? "risk-watch" : "risk-low")}
        ${metric("총 뉴스", `${num(state.payload.newsItems.length)}건`, "수집", "blue")}
      </aside>
    </section>
    ${newsFeed("핵심 뉴스", news)}
  `;
  els.detail.innerHTML = detailForNews(selectedNews());
}

function regionNode(region, cls) {
  if (!region) return "";
  return `<button class="region ${cls}" type="button" data-region="${escapeHtml(region.region)}"><strong>${escapeHtml(localizeRegion(region.region))} <em class="${riskTone(region.risk)}">${num(region.pressure)}</em></strong><span>${escapeHtml(compact(region.summary, 24))}</span></button>`;
}

function englishDailyBriefing(date, briefing, items) {
  if (state.lang !== "en") return briefing;
  const translated = items.map(translatedItem).filter((item) => item.translated);
  const topSummaries = translated
    .slice(0, 3)
    .map((item) => item.summary)
    .filter(Boolean);
  return {
    title: `${date || "Selected Date"} Daily Briefing`,
    summary: topSummaries.length
      ? `Key developments: ${topSummaries.join(" ")}`
      : "English translations are being prepared for this date. Korean source text may appear until translation is complete.",
    maxRisk: briefing.maxRisk,
  };
}

function renderDaily() {
  const dates = dateList();
  const date = currentDate();
  const items = newsForDate(date).sort((a, b) => String(b.publishedAt || "").localeCompare(String(a.publishedAt || "")));
  const briefing = englishDailyBriefing(date, state.payload.dailyBriefings[date] || {}, items);
  const avg = items.reduce((total, item) => total + Number(item.impact || 0), 0) / Math.max(items.length, 1);
  els.content.innerHTML = `
    <section class="panel panel-pad daily-head">
      <div>
        <p class="eyebrow">Daily Briefing</p>
        <h2>${escapeHtml(briefing.title || `${date || (state.lang === "en" ? "Today" : "오늘")} ${state.lang === "en" ? "News" : "뉴스"}`)}</h2>
        <p>${escapeHtml(briefing.summary || (state.lang === "en" ? "Review analyzed news by date." : "분석된 뉴스를 날짜별로 확인합니다."))}</p>
      </div>
      <label class="date-select">${escapeHtml(ui("날짜"))}
        <select id="dateSelect">${dates.map((item) => `<option value="${item}" ${item === date ? "selected" : ""}>${item}</option>`).join("")}</select>
      </label>
    </section>
    <section class="cards">
      ${smallCard("수집 뉴스", state.lang === "en" ? formatCount(items.length) : `${num(items.length)}건`)}
      ${smallCard("평균 영향도", avg.toFixed(1), "blue")}
      ${smallCard("최고 위험", localizeRisk(briefing.maxRisk || items[0]?.risk || "-"), riskTone(briefing.maxRisk || items[0]?.risk))}
    </section>
    ${newsFeed(state.lang === "en" ? `${date || "Selected Date"} News` : `${date || "선택 날짜"} 뉴스`, items)}
  `;
  els.detail.innerHTML = detailForNews(selectedNews());
}

function renderFlows() {
  const issues = state.payload.issues || [];
  const html = issues.length
    ? issues.map((issue) => `
      <article class="flow-item">
        <div class="flow-date">${escapeHtml(issue.updatedAt || issue.firstSeen || "-")}</div>
        <div>
          <h3>${escapeHtml(issue.title)}</h3>
          <p class="summary">${escapeHtml(compact(issue.summary, 160))}</p>
          <div class="chips">${(issue.events || []).slice(-3).map((event) => `<span class="chip">${escapeHtml(event.date || "")} ${escapeHtml(compact(event.text, 45))}</span>`).join("")}</div>
        </div>
        <span class="risk-watch">${num(issue.impact, 1)}</span>
      </article>
    `).join("")
    : `<p class="empty">이슈 흐름 데이터가 아직 없습니다.</p>`;
  els.content.innerHTML = `<section class="panel"><div class="feed-head"><h2>진행 중인 이슈 타임라인</h2><div class="tabs"><span class="active">전체</span><span>중동</span><span>중국</span><span>금리</span></div></div><div class="flow">${html}</div></section>`;
  els.detail.innerHTML = detailBlock("흐름 요약", "단일 뉴스보다 중요한 것은 사건의 누적 방향입니다. 같은 이슈가 반복되면 AI가 흐름으로 묶고 현재 국면을 판단합니다.");
}

function renderRegions() {
  const regions = state.payload.regionViews || [];
  if (!state.selectedRegion && regions[0]) state.selectedRegion = regions[0].region;
  const html = regions.map((region) => `
    <button class="card region-card ${region.region === state.selectedRegion ? "active" : ""}" type="button" data-region="${escapeHtml(region.region)}">
      <label>${escapeHtml(region.region)}</label>
      <strong class="${riskTone(region.risk)}">${num(region.pressure)}</strong>
      <p class="summary">${escapeHtml(compact(region.summary, 90))}</p>
    </button>
  `).join("");
  els.content.innerHTML = `<section class="cards">${html || `<p class="empty">지역 리스크 데이터가 없습니다.</p>`}</section>${newsFeed("지역 관련 고영향 뉴스", highImpactNews(5))}`;
  const selected = regions.find((region) => region.region === state.selectedRegion) || regions[0];
  els.detail.innerHTML = selected ? detailBlock(`${selected.region} 리스크`, selected.summary || "지역 리스크 요약이 없습니다.") : detailBlock("지역 리스크", "지역을 선택하면 상세가 표시됩니다.");
}

function renderAssets() {
  const assets = state.payload.assetViews || [];
  if (!state.selectedAsset && assets[0]) state.selectedAsset = assets[0].name;
  const rows = assets.map((asset) => `
    <button class="asset-row" type="button" data-asset="${escapeHtml(asset.name)}">
      <strong>${escapeHtml(asset.name)}</strong>
      <span><p class="summary">${escapeHtml(compact(asset.summary, 110))}</p><span class="bar"><i style="width:${Math.min(Number(asset.impact || 0) * 10, 100)}%"></i></span></span>
      <em class="${impactTone(asset.impact)}">${num(asset.impact, 1)}</em>
    </button>
  `).join("");
  els.content.innerHTML = `<section class="panel"><div class="feed-head"><h2>자산별 민감도</h2><div class="tabs"><span class="active">전체</span><span>원자재</span><span>주식</span><span>환율</span></div></div>${rows || `<p class="empty">자산 영향 데이터가 없습니다.</p>`}</section>`;
  const selected = assets.find((asset) => asset.name === state.selectedAsset) || assets[0];
  els.detail.innerHTML = selected ? detailBlock(`${selected.name} 영향`, selected.summary || "자산 영향 요약이 없습니다.") : detailBlock("자산 영향", "자산을 선택하면 상세가 표시됩니다.");
}

function assetHubTypeLabel(kind, fallback = "자산") {
  return ({ stock: "주식", etf: "ETF", index: "지수", other: "원자재·환율·가상자산", indicator: "시장 지표" })[kind] || fallback;
}

function assetHubItems() {
  const themes = (state.payload.assetViews || []).map((asset) => ({ ...asset, sourceType: "theme", searchTerms: [asset.name, asset.type, ...(asset.watch || [])] }));
  const instruments = (state.marketAssets || []).map((asset) => {
    const terms = [asset.name, asset.symbol, asset.group, ...(asset.keywords || [])].filter(Boolean);
    const relatedTheme = themes.find((theme) => terms.some((term) => `${theme.name} ${theme.type} ${(theme.watch || []).join(" ")}`.toLowerCase().includes(String(term).toLowerCase())));
    return {
      name: asset.name,
      symbol: asset.symbol,
      type: assetHubTypeLabel(asset.kind, asset.group),
      stance: relatedTheme?.stance || "뉴스·가격 관찰",
      impact: relatedTheme?.impact || 0,
      summary: relatedTheme?.summary || `${asset.name}(${asset.symbol})의 가격 흐름과 관련 뉴스를 함께 추적합니다.`,
      watch: [...new Set([...(asset.keywords || []), asset.group].filter(Boolean))].slice(0, 7),
      searchTerms: terms,
      sourceType: "instrument",
      marketKind: asset.kind,
    };
  });
  const names = new Set();
  return [...instruments, ...themes].filter((asset) => {
    const key = asset.name.toLowerCase();
    if (names.has(key)) return false;
    names.add(key);
    return true;
  });
}

function assetRelatedNews(asset, limit = 10) {
  if (!asset) return [];
  const terms = [...new Set([asset.name, asset.symbol, asset.type, ...(asset.searchTerms || []), ...(asset.watch || [])]
    .map((term) => String(term || "").trim().toLowerCase()).filter((term) => term.length >= 2))];
  const evidencePool = [...latestNews(), ...(state.payload.sourceDocuments || [])];
  const ranked = evidencePool.map((item) => {
    const title = String(item.title || "").toLowerCase();
    const body = `${item.summary || ""} ${item.analysis || ""} ${item.rawText || ""}`.toLowerCase();
    const tags = `${(item.tags || []).join(" ")} ${item.topic || ""} ${item.country || ""} ${item.source || ""}`.toLowerCase();
    let relevance = 0;
    terms.forEach((term, index) => {
      const weight = index < 2 ? 5 : term.length >= 5 ? 3 : 1;
      if (title.includes(term)) relevance += weight * 3;
      if (tags.includes(term)) relevance += weight * 2;
      if (body.includes(term)) relevance += weight;
    });
    return { ...item, relevance: relevance + (item.document && relevance > 0 ? 2 : 0) };
  }).filter((item) => item.relevance > 0).sort((a, b) => b.relevance - a.relevance || Number(b.impact || 0) - Number(a.impact || 0));
  if (ranked.length >= limit) return ranked.slice(0, limit);
  const used = new Set(ranked.map((item) => item.id));
  const context = latestNews().filter((item) => !used.has(item.id) && Number(item.impact || 0) >= 7).slice(0, limit - ranked.length).map((item) => ({ ...item, contextual: true }));
  return [...ranked, ...context].slice(0, limit);
}

function assetIconMarkup(asset, size = "card") {
  const raw = String(asset?.symbol || asset?.name || "A").replace(/^\^/, "").split(".")[0];
  const initials = asset?.symbol ? raw.slice(0, 4) : raw.split(/\s|·|\//).filter(Boolean).map((part) => part[0]).join("").slice(0, 3);
  const brandSlugs = {
    AAPL: "apple", MSFT: "microsoft", GOOGL: "google", AMZN: "amazon", META: "meta", NVDA: "nvidia",
    AVGO: "broadcom", AMD: "amd", MU: "micron", TSLA: "tesla", JPM: "jpmorgan", XOM: "exxonmobil",
    "005930.KS": "samsung", "005380.KS": "hyundai", "035420.KS": "naver", "BTC-USD": "bitcoin", "ETH-USD": "ethereum",
  };
  const indexLabels = {
    "^GSPC": "SPX", "^IXIC": "NAS", "^DJI": "DJI", "^RUT": "RUT", "^KS11": "KOSPI", "^KQ11": "KQ",
    "^N225": "N225", "^HSI": "HSI", "000001.SS": "SSE", "^STOXX50E": "SX5E", "^FTSE": "FTSE", "^GDAXI": "DAX",
  };
  if (asset?.marketKind === "index") {
    return `<span class="asset-logo asset-index-badge ${size}" aria-hidden="true"><b>${escapeHtml(indexLabels[asset.symbol] || raw.slice(0, 5))}</b></span>`;
  }
  if (asset?.marketKind === "etf") {
    return `<span class="asset-logo asset-etf-badge ${size}" aria-hidden="true"><b>${escapeHtml(raw.slice(0, 5))}</b><small>ETF</small></span>`;
  }
  const genericIcon = asset?.marketKind === "index" ? "material-symbols/monitoring-rounded"
    : /gold|금/i.test(`${asset?.name} ${asset?.watch}`) ? "material-symbols/diamond-outline-rounded"
    : /oil|wti|원유|에너지/i.test(`${asset?.name} ${asset?.watch}`) ? "mdi/oil"
    : /usd|krw|달러|통화|환율/i.test(`${asset?.name} ${asset?.watch}`) ? "material-symbols/currency-exchange-rounded"
    : /bond|yield|금리|국채/i.test(`${asset?.name} ${asset?.watch}`) ? "material-symbols/account-balance-rounded"
    : /방산|지정학/i.test(`${asset?.name} ${asset?.watch}`) ? "material-symbols/security-rounded"
    : /반도체|ai|기술/i.test(`${asset?.name} ${asset?.watch}`) ? "material-symbols/memory-rounded"
    : "material-symbols/query-stats-rounded";
  const slug = brandSlugs[asset?.symbol];
  const url = slug ? `https://cdn.simpleicons.org/${slug}` : `https://api.iconify.design/${genericIcon}.svg?color=%2316834f`;
  const fallbackUrl = "https://api.iconify.design/material-symbols/domain-rounded.svg?color=%2316834f";
  return `<span class="asset-logo ${size}" aria-hidden="true"><img src="${url}" data-fallback-src="${fallbackUrl}" alt="" loading="lazy"><span class="asset-logo-fallback" hidden>${escapeHtml(initials || raw.slice(0, 2))}</span></span>`;
}

function renderAssetHub() {
  if (!state.marketAssets.length) {
    loadMarketAssets().then(() => { if (state.view === "assets") renderAssetHub(); }).catch((error) => console.info(error));
  }
  const allAssets = assetHubItems();
  const categories = [...new Set(allAssets.map((asset) => asset.type).filter(Boolean))];
  const query = state.assetHubSearch.trim().toLowerCase();
  const assets = allAssets.filter((asset) => (state.assetHubFilter === "all" || asset.type === state.assetHubFilter) && (!query || `${asset.name} ${asset.symbol || ""} ${asset.type} ${asset.stance} ${asset.summary} ${(asset.searchTerms || []).join(" ")}`.toLowerCase().includes(query)));
  if (!state.selectedAsset || !allAssets.some((asset) => asset.name === state.selectedAsset)) state.selectedAsset = allAssets[0]?.name || "";
  const selected = allAssets.find((asset) => asset.name === state.selectedAsset) || assets[0] || allAssets[0];
  const related = assetRelatedNews(selected);
  const earnings = (state.payload.calendarEvents || []).filter((item) => item.category === "earnings" && new Date(item.scheduledAt) >= new Date()).sort((a, b) => new Date(a.scheduledAt) - new Date(b.scheduledAt)).slice(0, 5);
  const cards = assets.length ? assets.map((asset) => `
    <button type="button" class="asset-hub-card ${asset.name === state.selectedAsset ? "active" : ""}" data-asset="${escapeHtml(asset.name)}">
      <div class="asset-hub-card-head">${assetIconMarkup(asset)}<span><b>${escapeHtml(asset.type || "자산")}</b><em>${escapeHtml(asset.symbol || asset.stance || "관찰")}</em></span></div><h3>${escapeHtml(asset.name)}</h3>
      <p>${escapeHtml(compact(asset.summary || "관련 시장 신호를 확인하세요.", 90))}</p><footer><span>영향도</span><strong class="${impactTone(asset.impact)}">${num(asset.impact, 1)}</strong></footer>
    </button>`).join("") : `<p class="empty">조건에 맞는 자산이 없습니다.</p>`;
  const newsRows = related.length ? related.map((item) => item.document
    ? `<a class="asset-news-row evidence-document" href="${escapeHtml(safeExternalUrl(item.sourceUrl))}" target="_blank" rel="noopener noreferrer"><span><small>공식·보강 근거 · ${escapeHtml(item.source || "출처")}</small><b>${escapeHtml(item.title || "제목 없음")}</b></span><strong>↗</strong></a>`
    : `<button type="button" class="asset-news-row" data-view="daily" data-news-id="${item.id}"><span>${item.contextual ? '<small>시장 전반</small>' : `<small>관련도 ${num(item.relevance || 0)}</small>`}<b>${escapeHtml(item.title || "제목 없음")}</b></span><strong class="${impactTone(item.impact)}">${num(item.impact, 1)}</strong></button>`).join("") : `<p class="empty">연결된 최신 뉴스가 없습니다.</p>`;
  const earningsRows = earnings.length ? earnings.map((item) => {
    const label = new Date(item.scheduledAt).toLocaleString("ko-KR", { timeZone: "Asia/Seoul", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
    return `<button type="button" class="asset-earnings-row" data-go="calendar"><time>${escapeHtml(label)}</time><span>${escapeHtml(item.title)}</span></button>`;
  }).join("") : `<p class="empty">예정된 주요 실적 발표가 없습니다.</p>`;
  els.content.innerHTML = `
    <section class="panel asset-hub-hero"><div><span>ASSET INTELLIGENCE</span><h2>종목·자산 허브</h2><p>뉴스 영향도와 핵심 관찰 변수, 관련 일정과 가격 차트를 연결해서 확인합니다.</p></div><label class="asset-hub-search"><span>검색</span><input id="assetHubSearch" type="search" value="${escapeHtml(state.assetHubSearch)}" placeholder="반도체, 달러, 원유…"></label></section>
    <section class="asset-hub-tabs" aria-label="자산 유형"><button type="button" data-asset-filter="all" class="${state.assetHubFilter === "all" ? "active" : ""}">전체 <span>${allAssets.length}</span></button>${categories.map((category) => `<button type="button" data-asset-filter="${escapeHtml(category)}" class="${state.assetHubFilter === category ? "active" : ""}">${escapeHtml(category)} <span>${allAssets.filter((asset) => asset.type === category).length}</span></button>`).join("")}</section>
    <section class="asset-hub-grid">${cards}</section>
    <section class="asset-hub-lower"><div class="panel asset-hub-news"><div class="home-section-head"><div><span>RELATED NEWS</span><h2>${escapeHtml(selected?.name || "선택 자산")} 관련 뉴스</h2></div><button type="button" data-go="daily">전체 뉴스</button></div>${newsRows}</div><aside class="panel asset-hub-earnings"><div class="home-section-head"><div><span>UPCOMING EARNINGS</span><h2>주요 실적 발표</h2></div><button type="button" data-go="calendar">캘린더</button></div>${earningsRows}</aside></section>`;
  els.detail.innerHTML = selected ? `
    <div class="asset-detail-heading">${assetIconMarkup(selected, "detail")}<span><small>${escapeHtml(selected.type || "자산")}</small><h2>${escapeHtml(selected.name)}</h2></span></div><div class="asset-detail-score"><span>뉴스 영향도</span><strong class="${impactTone(selected.impact)}">${num(selected.impact, 1)}</strong></div>
    <div class="detail-section"><div class="detail-title">현재 판단</div><p>${escapeHtml(selected.stance || "관찰")}</p></div><div class="detail-section"><div class="detail-title">핵심 요약</div><p>${escapeHtml(selected.summary || "요약이 없습니다.")}</p></div>
    <div class="detail-section"><div class="detail-title">관찰 변수</div><div class="asset-watch-chips">${(selected.watch || []).map((item) => `<span>${escapeHtml(item)}</span>`).join("") || "<span>등록된 변수가 없습니다.</span>"}</div></div>
    <div class="detail-actions"><button type="button" class="analysis-action ${isAssetWatched(selected) ? "watching" : ""}" data-watch-asset="${escapeHtml(assetWatchKey(selected))}">${isAssetWatched(selected) ? "★ 관심 해제" : "☆ 관심 추가"}</button><button type="button" class="analysis-action" data-go="market">가격 차트 보기</button><button type="button" class="analysis-action secondary" data-go="ai">AI에 질문하기</button></div>` : `<h2>종목·자산 허브</h2><p class="empty">자산을 선택하면 상세 정보가 표시됩니다.</p>`;
}

function assetWatchKey(asset) {
  return String(asset?.symbol || asset?.name || "");
}

function isAssetWatched(asset) {
  return state.watchlist.includes(assetWatchKey(asset));
}

function toggleWatchedAsset(key) {
  const cleanKey = String(key || "");
  if (!cleanKey) return;
  state.watchlist = state.watchlist.includes(cleanKey) ? state.watchlist.filter((item) => item !== cleanKey) : [...state.watchlist, cleanKey];
  localStorage.setItem("eminai_watchlist", JSON.stringify(state.watchlist));
}

function renderWatchlist() {
  if (!state.marketAssets.length) loadMarketAssets().then(() => { if (state.view === "watchlist") renderWatchlist(); }).catch((error) => console.info(error));
  const catalog = assetHubItems();
  const watched = state.watchlist.map((key) => catalog.find((asset) => assetWatchKey(asset) === key)).filter(Boolean);
  const cards = watched.length ? watched.map((asset) => {
    const related = assetRelatedNews(asset, 3).filter((item) => !item.document);
    return `<article class="watchlist-card">
      <div class="watchlist-card-head">${assetIconMarkup(asset)}<span><small>${escapeHtml(asset.type || "자산")}</small><h3>${escapeHtml(asset.name)}</h3><em>${escapeHtml(asset.symbol || asset.stance || "관찰")}</em></span><button type="button" data-watch-asset="${escapeHtml(assetWatchKey(asset))}" aria-label="관심 목록에서 제거">★</button></div>
      <div class="watchlist-signal"><span>현재 판단</span><strong>${escapeHtml(asset.stance || "관찰")}</strong><em class="${impactTone(asset.impact)}">${num(asset.impact, 1)}</em></div>
      <div class="watchlist-news">${related.map((item) => `<button type="button" data-view="daily" data-news-id="${item.id}">${escapeHtml(compact(item.title || "관련 뉴스", 58))}</button>`).join("") || "<p>연결된 최신 뉴스가 없습니다.</p>"}</div>
      <footer><button type="button" data-asset="${escapeHtml(asset.name)}" data-open-asset="1">자산 상세</button>${asset.symbol ? `<button type="button" data-watch-chart="${escapeHtml(asset.symbol)}">가격 차트</button>` : ""}</footer>
    </article>`;
  }).join("") : `<section class="panel watchlist-empty"><span>☆</span><h2>아직 관심 자산이 없습니다</h2><p>종목·자산 허브에서 관심 추가를 누르면 이곳에 모아볼 수 있습니다.</p><button type="button" data-go="assets">자산 둘러보기</button></section>`;
  const events = (state.payload.calendarEvents || []).filter((event) => event.category === "earnings" && new Date(event.scheduledAt) >= new Date()).slice(0, 6);
  els.content.innerHTML = `<section class="panel watchlist-hero"><div><span>MY WATCHLIST</span><h2>관심 자산 ${watched.length}개</h2><p>이 브라우저에 저장되며 선택한 자산의 뉴스와 주요 일정을 빠르게 확인합니다.</p></div><button type="button" data-go="assets">+ 자산 추가</button></section><section class="watchlist-grid">${cards}</section>${watched.length ? `<section class="panel watchlist-events"><div class="home-section-head"><div><span>UPCOMING</span><h2>다가오는 주요 실적</h2></div><button type="button" data-go="calendar">전체 일정</button></div>${events.map((event) => `<button type="button" data-go="calendar"><time>${new Date(event.scheduledAt).toLocaleString("ko-KR", { timeZone:"Asia/Seoul", month:"2-digit", day:"2-digit", hour:"2-digit", minute:"2-digit" })}</time><span>${escapeHtml(event.title)}</span></button>`).join("")}</section>` : ""}`;
  els.detail.innerHTML = `<h2>관심 자산</h2><div class="detail-section"><div class="detail-title">저장 방식</div><p>현재 사용하는 브라우저에 저장됩니다. 브라우저 데이터를 삭제하면 관심 목록도 초기화됩니다.</p></div><div class="detail-section"><div class="detail-title">활용 방법</div><p>자산별 관련 뉴스와 영향도를 비교하고, 가격 차트와 실적 일정을 이어서 확인하세요.</p></div>`;
}

function renderNewsHub() {
  const query = state.newsHubQuery.trim().toLowerCase();
  const itemDateKey = (item) => String(item.date || item.publishedAt || "").slice(0, 10);
  const regionMatches = (item) => state.newsHubRegion === "all" || (state.newsHubRegion === "US" ? /미국|US|USA/i.test(`${item.region || ""} ${item.country || ""} ${(item.tags || []).join(" ")}`) : /한국|KR|Korea/i.test(`${item.region || ""} ${item.country || ""} ${(item.tags || []).join(" ")}`));
  const topicMatches = (item) => {
    if (state.newsHubTopic === "all") return true;
    const text = `${item.category || ""} ${item.topic || ""} ${(item.tags || []).join(" ")}`;
    if (state.newsHubTopic === "macro") return /macro|inflation|labor|production|consumption|trade|external_balance|economy|거시|물가|고용|생산|소비|수출/i.test(text);
    if (state.newsHubTopic === "policy") return /policy|monetary|central|fed|bok|금리|연준|한국은행|통화/i.test(text);
    if (state.newsHubTopic === "earnings") return /earnings|실적|기업/i.test(text);
    if (state.newsHubTopic === "geopolitics") return /geopolitics|war|military|sanction|지정학|전쟁|군사|제재|중동|이란|러시아|우크라이나/i.test(text);
    return /market|markets|stock|asset|증시|주식|채권|환율|원유/i.test(text);
  };
  const byDate = (item) => Date.parse(item.publishedAt || item.date || 0) || 0;
  const sorter = state.newsHubSort === "impact" ? (a, b) => Number(b.impact || 0) - Number(a.impact || 0) || byDate(b) - byDate(a) : (a, b) => byDate(b) - byDate(a);
  const dateMatches = (item) => state.newsHubDate === "all" || itemDateKey(item) === state.newsHubDate;
  const news = latestNews().filter((item) => state.newsHubImpact !== "high" || Number(item.impact || 0) >= 8).filter(regionMatches).filter(topicMatches).filter(dateMatches).filter((item) => !query || `${item.title} ${item.summary} ${item.analysis} ${(item.tags || []).join(" ")} ${item.source || ""}`.toLowerCase().includes(query)).sort(sorter);
  const documents = (state.payload.sourceDocuments || []).filter(regionMatches).filter(topicMatches).filter(dateMatches).filter((item) => !query || `${item.title} ${item.summary} ${item.topic} ${item.country} ${item.source}`.toLowerCase().includes(query)).sort(sorter);
  const visibleNews = state.newsHubSource === "documents" ? [] : news;
  const visibleDocuments = state.newsHubSource === "news" ? [] : documents;
  const allDocuments = state.payload.sourceDocuments || [];
  const sourceCount = new Set(allDocuments.map((item) => item.source).filter(Boolean)).size;
  const activeFilterCount = [state.newsHubSource !== "all", state.newsHubImpact !== "all", state.newsHubRegion !== "all", state.newsHubTopic !== "all", state.newsHubDate !== "all", Boolean(query)].filter(Boolean).length;
  const availableDates = [...new Set([...latestNews(), ...allDocuments].map(itemDateKey).filter(Boolean))].sort().reverse();
  const mergedItems = [
    ...visibleNews.map((item) => ({ ...item, evidenceType:"news" })),
    ...visibleDocuments.map((item) => ({ ...item, evidenceType:"document" })),
  ].sort(sorter);
  let previousDate = "";
  const rows = mergedItems.map((item) => {
    const dateKey = itemDateKey(item) || "날짜 미상";
    const heading = state.newsHubSort === "latest" && dateKey !== previousDate ? `<div class="news-date-heading"><time>${escapeHtml(dateKey)}</time><span>${mergedItems.filter((entry) => itemDateKey(entry) === dateKey).length}건</span></div>` : "";
    previousDate = dateKey;
    const row = item.evidenceType === "document"
      ? `<a class="news-hub-row" href="${escapeHtml(safeExternalUrl(item.sourceUrl))}" target="_blank" rel="noopener noreferrer"><span class="news-hub-source official">공식</span><span><small>${escapeHtml(item.source || "공식자료")} · ${escapeHtml(item.publishedAt || "")}</small><b>${escapeHtml(item.title || "제목 없음")}</b><p>${escapeHtml(compact(item.summary || "", 120))}</p></span><em>↗</em></a>`
      : `<button type="button" class="news-hub-row" data-news-id="${item.id}"><span class="news-hub-source telegram">TG</span><span><small>${escapeHtml(item.source || "insidertracking")} · ${escapeHtml(item.publishedAt || item.newsDate || item.date || item.time || "")}</small><b>${escapeHtml(item.title || "제목 없음")}</b><p>${escapeHtml(compact(item.summary || item.rawText || "", 120))}</p></span><em class="${impactTone(item.impact)}">${num(item.impact,1)}</em></button>`;
    return heading + row;
  });
  els.content.innerHTML = `<section class="panel news-hub-hero"><div><span>NEWS & EVIDENCE</span><h2>뉴스·근거 허브</h2><p>수집 뉴스와 공식기관·기업 자료를 함께 검색합니다.</p><div class="news-hub-stats"><b>${state.payload.newsItems.length}<small>수집 뉴스</small></b><b>${allDocuments.length}<small>보강 근거</small></b><b>${sourceCount}<small>근거 출처</small></b></div></div><label><span>통합 검색</span><input id="newsHubSearch" type="search" value="${escapeHtml(state.newsHubQuery)}" placeholder="기업, 지표, 정책, 키워드 검색"></label></section><section class="news-hub-controls"><div><button type="button" data-news-source="all" class="${state.newsHubSource === "all" ? "active" : ""}">전체 ${news.length + documents.length}</button><button type="button" data-news-source="news" class="${state.newsHubSource === "news" ? "active" : ""}">수집 뉴스 ${news.length}</button><button type="button" data-news-source="documents" class="${state.newsHubSource === "documents" ? "active" : ""}">공식·보강 근거 ${documents.length}</button></div><div><button type="button" data-news-impact="all" class="${state.newsHubImpact === "all" ? "active" : ""}">전체 영향도</button><button type="button" data-news-impact="high" class="${state.newsHubImpact === "high" ? "active" : ""}">고영향 8+</button></div></section><section class="news-hub-facets"><div><span>지역</span>${[["all","전체"],["US","미국"],["KR","한국"]].map(([value,label]) => `<button type="button" data-news-region="${value}" class="${state.newsHubRegion === value ? "active" : ""}">${label}</button>`).join("")}</div><div><span>주제</span>${[["all","전체"],["macro","거시지표"],["policy","통화정책"],["markets","시장"],["earnings","기업실적"]].map(([value,label]) => `<button type="button" data-news-topic="${value}" class="${state.newsHubTopic === value ? "active" : ""}">${label}</button>`).join("")}</div><div><span>정렬</span><button type="button" data-news-sort="latest" class="${state.newsHubSort === "latest" ? "active" : ""}">최신순</button><button type="button" data-news-sort="impact" class="${state.newsHubSort === "impact" ? "active" : ""}">영향도순</button>${activeFilterCount ? `<button type="button" class="news-filter-reset" data-news-reset="1">필터 초기화 · ${activeFilterCount}</button>` : ""}</div></section><section class="panel news-hub-list">${rows.join("") || `<p class="empty">조건에 맞는 자료가 없습니다.</p>`}</section>`;
  els.content.querySelector(".news-hub-facets")?.insertAdjacentHTML("beforeend", `<div class="news-date-filter"><span>날짜</span><select id="newsHubDate" aria-label="뉴스 날짜"><option value="all">전체 날짜</option>${availableDates.map((date) => `<option value="${date}" ${state.newsHubDate === date ? "selected" : ""}>${date}</option>`).join("")}</select></div>`);
  els.detail.innerHTML = detailForNews(selectedNews());
}

function formatMarketPrice(value) {
  const price = Number(value || 0);
  const digits = price >= 1000 ? 0 : price >= 100 ? 2 : price >= 1 ? 3 : 5;
  return price.toLocaleString(undefined, { maximumFractionDigits: digits });
}

function formatMarketVolume(value) {
  const volume = Number(value || 0);
  if (volume >= 1_000_000_000) return `${(volume / 1_000_000_000).toFixed(2)}B`;
  if (volume >= 1_000_000) return `${(volume / 1_000_000).toFixed(2)}M`;
  if (volume >= 1_000) return `${(volume / 1_000).toFixed(1)}K`;
  return volume.toLocaleString();
}

function formatMarketDate(value, data, compact = false) {
  if (!value) return "-";
  if (data?.interval !== "4h") {
    if (!compact) return value;
    const [year, month, day] = String(value).split("-");
    return data?.interval === "1wk" ? `${year?.slice(2)}.${month}.${day}` : `${month}.${day}`;
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("ko-KR", compact
    ? { timeZone: data?.timezone || "UTC", month: "2-digit", day: "2-digit", hour: "2-digit", hour12: false }
    : { timeZone: data?.timezone || "UTC", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hour12: false }
  ).format(date);
}

function marketViewportKey(data) {
  return `${data?.asset?.symbol || ""}:${data?.range || ""}:${data?.interval || ""}:${data?.candles?.length || 0}`;
}

function ensureMarketViewport(data) {
  const total = data?.candles?.length || 0;
  const key = marketViewportKey(data);
  if (!state.marketChartViewport || state.marketChartViewport.key !== key) {
    state.marketChartViewport = { key, start: 0, end: total, priceScale: 1, priceOffset: 0 };
  }
  const viewport = state.marketChartViewport;
  viewport.start = Math.max(0, Math.min(viewport.start, Math.max(total - 1, 0)));
  viewport.end = Math.max(viewport.start + 1, Math.min(viewport.end, total));
  return viewport;
}

function visibleMarketCandles(data) {
  const viewport = ensureMarketViewport(data);
  return (data?.candles || []).slice(viewport.start, viewport.end);
}

function resetMarketViewport() {
  state.marketChartViewport = null;
}

function marketInspectorHtml(data) {
  const candle = visibleMarketCandles(data).at(-1);
  const candleChange = candle?.open ? (Number(candle.close) / Number(candle.open) - 1) * 100 : 0;
  return `
    <aside class="market-inspector" aria-label="선택 봉 상세 수치">
      <div class="market-inspector-head"><span>선택 봉</span><strong data-market-field="time">${escapeHtml(formatMarketDate(candle?.time, data))}</strong></div>
      <dl>
        <div><dt>시가</dt><dd data-market-field="open">${formatMarketPrice(candle?.open)}</dd></div>
        <div><dt>고가</dt><dd data-market-field="high">${formatMarketPrice(candle?.high)}</dd></div>
        <div><dt>저가</dt><dd data-market-field="low">${formatMarketPrice(candle?.low)}</dd></div>
        <div><dt>종가</dt><dd data-market-field="close">${formatMarketPrice(candle?.close)}</dd></div>
        <div><dt>봉 등락</dt><dd data-market-field="change" class="${candleChange >= 0 ? "value-up" : "value-down"}">${candleChange >= 0 ? "+" : ""}${candleChange.toFixed(2)}%</dd></div>
        <div><dt>거래량</dt><dd data-market-field="volume">${formatMarketVolume(candle?.volume)}</dd></div>
        <div><dt>MA20</dt><dd data-market-field="ma20">${candle?.ma20 == null ? "-" : formatMarketPrice(candle.ma20)}</dd></div>
      </dl>
      <p>${escapeHtml(data?.timezoneShortName || data?.timezone || "UTC")} 기준 · 차트 위에 마우스를 올려 확인</p>
    </aside>`;
}

function marketChartSvg(data) {
  const allCandles = data?.candles || [];
  if (!allCandles.length) return `<div class="market-empty">표시할 가격 데이터가 없습니다.</div>`;
  const viewport = ensureMarketViewport(data);
  const candles = visibleMarketCandles(data);
  const width = 1000;
  const height = 500;
  const left = 16;
  const right = 88;
  const priceTop = 18;
  const priceBottom = 365;
  const volumeTop = 395;
  const volumeBottom = 475;
  const lows = candles.map((item) => Number(item.low));
  const highs = candles.map((item) => Number(item.high));
  const naturalMin = Math.min(...lows);
  const naturalMax = Math.max(...highs);
  const padding = Math.max((naturalMax - naturalMin) * 0.06, Math.abs(naturalMax) * 0.002);
  const naturalSpan = Math.max(naturalMax - naturalMin + padding * 2, 0.000001);
  const priceSpan = Math.max(naturalSpan * viewport.priceScale, 0.000001);
  const priceCenter = (naturalMin + naturalMax) / 2 + naturalSpan * viewport.priceOffset;
  let minPrice = priceCenter - priceSpan / 2;
  let maxPrice = priceCenter + priceSpan / 2;
  const plotWidth = width - left - right;
  const step = plotWidth / Math.max(candles.length, 1);
  const candleWidth = Math.max(0.6, Math.min(8, step * 0.62));
  const maxVolume = Math.max(...candles.map((item) => Number(item.volume || 0)), 1);
  const x = (index) => left + step * index + step / 2;
  const y = (price) => priceTop + (maxPrice - Number(price)) / priceSpan * (priceBottom - priceTop);
  const grid = Array.from({ length: 6 }, (_, index) => {
    const ratio = index / 5;
    const gridY = priceTop + ratio * (priceBottom - priceTop);
    const label = maxPrice - ratio * priceSpan;
    return `<line x1="${left}" y1="${gridY}" x2="${width - right}" y2="${gridY}" class="market-grid-line"/><text x="${width - right + 8}" y="${gridY + 4}" text-anchor="start" class="market-axis">${escapeHtml(formatMarketPrice(label))}</text>`;
  }).join("");
  const candleSvg = candles.map((item, index) => {
    const up = Number(item.close) >= Number(item.open);
    const cls = up ? "up" : "down";
    const bodyTop = Math.min(y(item.open), y(item.close));
    const bodyHeight = Math.max(1.5, Math.abs(y(item.open) - y(item.close)));
    const volumeHeight = Number(item.volume || 0) / maxVolume * (volumeBottom - volumeTop);
    return `<g class="market-candle ${cls}"><line x1="${x(index)}" y1="${y(item.high)}" x2="${x(index)}" y2="${y(item.low)}"/><rect x="${x(index) - candleWidth / 2}" y="${bodyTop}" width="${candleWidth}" height="${bodyHeight}"/><rect class="market-volume" x="${x(index) - candleWidth / 2}" y="${volumeBottom - volumeHeight}" width="${candleWidth}" height="${volumeHeight}"/></g>`;
  }).join("");
  const maPoints = candles.map((item, index) => item.ma20 == null ? null : `${x(index)},${y(item.ma20)}`).filter(Boolean);
  const maPath = maPoints.length > 1 ? `<polyline points="${maPoints.join(" ")}" class="market-ma"/>` : "";
  const dateIndexes = [...new Set([0, Math.floor((candles.length - 1) * 0.25), Math.floor((candles.length - 1) / 2), Math.floor((candles.length - 1) * 0.75), candles.length - 1])];
  const dateLabels = dateIndexes.map((index) => `<text x="${x(index)}" y="494" text-anchor="middle" class="market-axis">${escapeHtml(formatMarketDate(candles[index].time, data, true))}</text>`).join("");
  const last = candles.at(-1);
  const lastY = Math.max(priceTop, Math.min(priceBottom, y(last.close)));
  const lastUp = Number(last.close) >= Number(last.open);
  const horizontalZoom = Math.round(allCandles.length / Math.max(candles.length, 1) * 100);
  const verticalZoom = Math.round(100 / viewport.priceScale);
  const visibleRange = `${formatMarketDate(candles[0]?.time, data, true)} – ${formatMarketDate(last?.time, data, true)}`;
  return `<div class="market-chart-tools">
      <div><strong>${escapeHtml(visibleRange)}</strong><span>X ${horizontalZoom}% · Y ${verticalZoom}%</span></div>
      <p>드래그: 상하·좌우 이동 · 휠: 시간축 확대 · Alt+휠: 가격축 확대</p>
      <div class="market-zoom-buttons"><button type="button" data-market-zoom="in" aria-label="차트 확대">＋</button><button type="button" data-market-zoom="out" aria-label="차트 축소">−</button><button type="button" data-market-zoom="reset">초기화</button></div>
    </div>
    <svg class="market-svg" data-market-chart data-plot-left="${left}" data-plot-right="${width - right}" data-price-top="${priceTop}" data-price-bottom="${priceBottom}" data-volume-bottom="${volumeBottom}" data-min-price="${minPrice}" data-max-price="${maxPrice}" viewBox="0 0 ${width} ${height}" role="img" aria-label="${escapeHtml(data.asset.name)} 가격 차트">
    <defs><clipPath id="market-plot-clip"><rect x="${left}" y="${priceTop}" width="${plotWidth}" height="${volumeBottom - priceTop}"/></clipPath></defs>
    ${grid}<line x1="${left}" y1="${volumeTop - 8}" x2="${width - right}" y2="${volumeTop - 8}" class="market-grid-line"/>
    <g data-market-plot clip-path="url(#market-plot-clip)">${candleSvg}${maPath}<line x1="${left}" y1="${lastY}" x2="${width - right}" y2="${lastY}" class="market-last-line ${lastUp ? "up" : "down"}"/></g>
    ${dateLabels}
    <text x="${left + 8}" y="${priceTop + 15}" class="market-ma-label">MA20</text>
    <g class="market-last-price ${lastUp ? "up" : "down"}"><rect x="${width - right + 3}" y="${lastY - 10}" width="82" height="20" rx="3"/><text x="${width - right + 44}" y="${lastY + 4}" text-anchor="middle">${escapeHtml(formatMarketPrice(last.close))}</text></g>
    <line data-crosshair-x class="market-crosshair" x1="${left}" y1="${priceTop}" x2="${left}" y2="${volumeBottom}" visibility="hidden"/>
    <line data-crosshair-y class="market-crosshair" x1="${left}" y1="${priceTop}" x2="${width - right}" y2="${priceTop}" visibility="hidden"/>
    <g data-crosshair-price class="market-crosshair-label" visibility="hidden"><rect x="${width - right + 3}" y="${priceTop - 10}" width="82" height="20" rx="3"/><text x="${width - right + 44}" y="${priceTop + 4}" text-anchor="middle">-</text></g>
    <g data-crosshair-date class="market-crosshair-label" visibility="hidden"><rect x="${left}" y="477" width="136" height="21" rx="3"/><text x="${left + 68}" y="492" text-anchor="middle">-</text></g>
    <rect class="market-hit-area" x="${left}" y="${priceTop}" width="${plotWidth}" height="${volumeBottom - priceTop}"/>
  </svg>`;
}

function updateMarketInspector(candle, data) {
  if (!candle) return;
  const change = candle.open ? (Number(candle.close) / Number(candle.open) - 1) * 100 : 0;
  const values = {
    time: formatMarketDate(candle.time, data),
    open: formatMarketPrice(candle.open),
    high: formatMarketPrice(candle.high),
    low: formatMarketPrice(candle.low),
    close: formatMarketPrice(candle.close),
    change: `${change >= 0 ? "+" : ""}${change.toFixed(2)}%`,
    volume: formatMarketVolume(candle.volume),
    ma20: candle.ma20 == null ? "-" : formatMarketPrice(candle.ma20),
  };
  Object.entries(values).forEach(([field, value]) => {
    const target = els.content.querySelector(`[data-market-field="${field}"]`);
    if (!target) return;
    target.textContent = value;
    if (field === "change") target.className = change >= 0 ? "value-up" : "value-down";
  });
}

function refreshMarketChartStage(data) {
  const stage = els.content.querySelector("[data-market-chart-stage]");
  if (!stage || !data) return;
  stage.innerHTML = `<div class="market-chart-wrap" data-market-chart-wrap>${marketChartSvg(data)}</div>${marketInspectorHtml(data)}`;
  bindMarketChartInteractions(data);
}

function zoomMarketChart(data, action, anchor = 0.5, axes = { horizontal: true, vertical: true }) {
  const total = data?.candles?.length || 0;
  if (!total) return;
  if (action === "reset") {
    state.marketChartViewport = { key: marketViewportKey(data), start: 0, end: total, priceScale: 1, priceOffset: 0 };
    refreshMarketChartStage(data);
    return;
  }
  const viewport = ensureMarketViewport(data);
  const directionFactor = action === "in" ? 0.75 : 1 / 0.75;
  if (axes.horizontal) {
    const currentSpan = viewport.end - viewport.start;
    const minimumSpan = Math.min(total, 12);
    const nextSpan = Math.max(minimumSpan, Math.min(total, Math.round(currentSpan * directionFactor)));
    const anchorIndex = viewport.start + currentSpan * Math.max(0, Math.min(anchor, 1));
    const nextStart = Math.max(0, Math.min(total - nextSpan, Math.round(anchorIndex - nextSpan * anchor)));
    viewport.start = nextStart;
    viewport.end = nextStart + nextSpan;
  }
  if (axes.vertical) {
    viewport.priceScale = Math.max(0.2, Math.min(5, viewport.priceScale * (action === "in" ? 0.8 : 1.25)));
  }
  refreshMarketChartStage(data);
}

function panMarketChart(data, horizontalRatio, verticalRatio) {
  const total = data?.candles?.length || 0;
  if (!total) return;
  const viewport = ensureMarketViewport(data);
  const span = viewport.end - viewport.start;
  const shift = Math.round(-horizontalRatio * span);
  const nextStart = Math.max(0, Math.min(total - span, viewport.start + shift));
  viewport.start = nextStart;
  viewport.end = nextStart + span;
  viewport.priceOffset = Math.max(-4, Math.min(4, viewport.priceOffset + verticalRatio * viewport.priceScale));
  refreshMarketChartStage(data);
}

function bindMarketChartInteractions(data) {
  const svg = els.content.querySelector("[data-market-chart]");
  if (!svg || !data?.candles?.length) return;
  const candles = visibleMarketCandles(data);
  const left = Number(svg.dataset.plotLeft);
  const right = Number(svg.dataset.plotRight);
  const priceTop = Number(svg.dataset.priceTop);
  const priceBottom = Number(svg.dataset.priceBottom);
  const volumeBottom = Number(svg.dataset.volumeBottom);
  const minPrice = Number(svg.dataset.minPrice);
  const maxPrice = Number(svg.dataset.maxPrice);
  const crossX = svg.querySelector("[data-crosshair-x]");
  const crossY = svg.querySelector("[data-crosshair-y]");
  const priceLabel = svg.querySelector("[data-crosshair-price]");
  const dateLabel = svg.querySelector("[data-crosshair-date]");
  const plotGroup = svg.querySelector("[data-market-plot]");
  const visibility = (value) => [crossX, crossY, priceLabel, dateLabel].forEach((item) => item?.setAttribute("visibility", value));
  let dragState = null;
  svg.addEventListener("pointermove", (event) => {
    const bounds = svg.getBoundingClientRect();
    if (dragState) {
      const deltaX = event.clientX - dragState.x;
      const deltaY = event.clientY - dragState.y;
      const svgX = deltaX / Math.max(bounds.width, 1) * 1000;
      const svgY = deltaY / Math.max(bounds.height, 1) * 500;
      plotGroup?.setAttribute("transform", `translate(${svgX} ${svgY})`);
      dragState.deltaX = deltaX;
      dragState.deltaY = deltaY;
      return;
    }
    const pointX = (event.clientX - bounds.left) / bounds.width * 1000;
    const pointY = (event.clientY - bounds.top) / bounds.height * 500;
    if (pointX < left || pointX > right || pointY < priceTop || pointY > volumeBottom) {
      visibility("hidden");
      return;
    }
    const ratio = (pointX - left) / Math.max(right - left, 1);
    const index = Math.max(0, Math.min(candles.length - 1, Math.floor(ratio * candles.length)));
    const candle = candles[index];
    const selectedX = left + (index + 0.5) * (right - left) / candles.length;
    const selectedY = Math.max(priceTop, Math.min(priceBottom, pointY));
    const cursorPrice = maxPrice - (selectedY - priceTop) / Math.max(priceBottom - priceTop, 1) * (maxPrice - minPrice);
    crossX.setAttribute("x1", selectedX); crossX.setAttribute("x2", selectedX);
    crossY.setAttribute("y1", selectedY); crossY.setAttribute("y2", selectedY);
    const priceRect = priceLabel.querySelector("rect");
    const priceText = priceLabel.querySelector("text");
    priceRect.setAttribute("y", selectedY - 10); priceText.setAttribute("y", selectedY + 4); priceText.textContent = formatMarketPrice(cursorPrice);
    const labelX = Math.max(left + 68, Math.min(right - 68, selectedX));
    const dateRect = dateLabel.querySelector("rect");
    const dateText = dateLabel.querySelector("text");
    dateRect.setAttribute("x", labelX - 68); dateText.setAttribute("x", labelX); dateText.textContent = formatMarketDate(candle.time, data, true);
    visibility("visible");
    updateMarketInspector(candle, data);
  });
  svg.addEventListener("pointerdown", (event) => {
    if (event.button !== 0) return;
    const bounds = svg.getBoundingClientRect();
    const pointX = (event.clientX - bounds.left) / bounds.width * 1000;
    const pointY = (event.clientY - bounds.top) / bounds.height * 500;
    if (pointX < left || pointX > right || pointY < priceTop || pointY > volumeBottom) return;
    dragState = { x: event.clientX, y: event.clientY, deltaX: 0, deltaY: 0 };
    visibility("hidden");
    svg.classList.add("dragging");
    svg.setPointerCapture?.(event.pointerId);
    event.preventDefault();
  });
  const finishDrag = (event) => {
    if (!dragState) return;
    const bounds = svg.getBoundingClientRect();
    const deltaX = dragState.deltaX;
    const deltaY = dragState.deltaY;
    dragState = null;
    plotGroup?.removeAttribute("transform");
    svg.classList.remove("dragging");
    if (svg.hasPointerCapture?.(event.pointerId)) svg.releasePointerCapture(event.pointerId);
    if (Math.abs(deltaX) < 3 && Math.abs(deltaY) < 3) return;
    const plotPixelWidth = bounds.width * (right - left) / 1000;
    const pricePixelHeight = bounds.height * (priceBottom - priceTop) / 500;
    panMarketChart(data, deltaX / Math.max(plotPixelWidth, 1), deltaY / Math.max(pricePixelHeight, 1));
  };
  svg.addEventListener("pointerup", finishDrag);
  svg.addEventListener("pointercancel", finishDrag);
  svg.addEventListener("wheel", (event) => {
    event.preventDefault();
    const bounds = svg.getBoundingClientRect();
    const pointX = (event.clientX - bounds.left) / bounds.width * 1000;
    const anchor = Math.max(0, Math.min(1, (pointX - left) / Math.max(right - left, 1)));
    const action = event.deltaY < 0 ? "in" : "out";
    if (event.altKey) zoomMarketChart(data, action, anchor, { horizontal: false, vertical: true });
    else zoomMarketChart(data, action, anchor, { horizontal: true, vertical: false });
  }, { passive: false });
  svg.addEventListener("dblclick", () => zoomMarketChart(data, "reset"));
  svg.addEventListener("pointerleave", () => {
    if (dragState) return;
    visibility("hidden");
    updateMarketInspector(candles.at(-1), data);
  });
}

function marketRelatedNews(asset) {
  const keywords = (asset?.keywords || []).map((item) => String(item).toLowerCase());
  if (!keywords.length) return [];
  return (state.payload.newsItems || []).filter((item) => {
    const text = [item.title, item.summary, item.analysis, ...(item.tags || [])].join(" ").toLowerCase();
    return keywords.some((keyword) => text.includes(keyword));
  }).slice(0, 6);
}

async function loadMarketAssets() {
  if (state.marketAssets.length) return;
  const response = await apiFetch("/api/market/assets", { cache: "no-store" });
  if (!response.ok) throw new Error(`market assets ${response.status}`);
  const payload = await response.json();
  state.marketAssets = payload.assets || [];
}

function formatIndicatorTimestamp(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return new Intl.DateTimeFormat("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: String(value).includes("T") ? "2-digit" : undefined,
    minute: String(value).includes("T") ? "2-digit" : undefined,
    hour12: false,
  }).format(date);
}

function formatCompactUsd(value) {
  const amount = Number(value || 0);
  if (Math.abs(amount) >= 1_000_000_000_000) return `$${(amount / 1_000_000_000_000).toFixed(2)}T`;
  if (Math.abs(amount) >= 1_000_000_000) return `$${(amount / 1_000_000_000).toFixed(1)}B`;
  if (Math.abs(amount) >= 1_000_000) return `$${(amount / 1_000_000).toFixed(1)}M`;
  return `$${amount.toLocaleString("ko-KR")}`;
}

function formatIndicatorNumber(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) return "-";
  const digits = Math.abs(number) >= 100 ? 1 : 2;
  return number.toLocaleString("ko-KR", { minimumFractionDigits: 0, maximumFractionDigits: digits });
}

function indicatorSupplementsHtml(item) {
  if (!(item.supplements || []).length) return "";
  return `<div class="indicator-supplements">${item.supplements.map((entry) => {
    const value = entry.format === "usdCompact" ? formatCompactUsd(entry.value) : `${formatIndicatorNumber(entry.value)}${entry.unit ? ` ${escapeHtml(entry.unit)}` : ""}`;
    return `<span><small>${escapeHtml(entry.label)}</small><strong>${value}</strong></span>`;
  }).join("")}</div>`;
}

function indicatorCardHtml(item) {
  const thresholds = (item.thresholds || []).map((band) => {
    const active = item.available && band.rangeText === item.currentRange;
    return `<span class="indicator-band ${active ? "active" : ""}" data-tone="${escapeHtml(band.tone || "muted")}"><small>${escapeHtml(band.rangeText)}</small><strong>${escapeHtml(band.label)}</strong></span>`;
  }).join("");
  const change = Number(item.changePercent);
  const changeText = Number.isFinite(change) && item.changePercent !== null ? `<em class="${change >= 0 ? "value-up" : "value-down"}">${change >= 0 ? "+" : ""}${change.toFixed(2)}% 일간</em>` : "";
  return `<article class="indicator-card" data-tone="${escapeHtml(item.tone || "muted")}">
    <div class="indicator-card-head"><span>${escapeHtml(item.category)}</span><strong>${escapeHtml(item.status)}</strong></div>
    <h3>${escapeHtml(item.name)}</h3>
    <div class="indicator-current"><b>${item.available ? formatIndicatorNumber(item.value) : "-"}</b><span>${escapeHtml(item.unit || "")}</span>${changeText}</div>
    <p>${escapeHtml(item.description || (item.available ? "현재 수치를 기준 구간과 비교합니다." : "현재 데이터를 불러오지 못했습니다."))}</p>
    ${indicatorSupplementsHtml(item)}
    <div class="indicator-thresholds" aria-label="${escapeHtml(item.name)} 판정 기준">${thresholds}</div>
    <div class="indicator-card-foot"><span>기준 ${escapeHtml(formatIndicatorTimestamp(item.asOf))}</span>${item.chartSymbol ? `<button type="button" data-market-symbol="${escapeHtml(item.chartSymbol)}">상세 차트</button>` : ""}</div>
    <div class="indicator-source">${item.sourceUrl ? `<a href="${escapeHtml(safeExternalUrl(item.sourceUrl))}" target="_blank" rel="noopener noreferrer">${escapeHtml(item.source)} 원문</a>` : `<span>${escapeHtml(item.source || "-")}</span>`}<small>${escapeHtml(item.note || "구간 기준은 대시보드 해석 규칙입니다.")}</small></div>
  </article>`;
}

const MACRO_GAUGE_SPECS = [
  {
    key: "inflation",
    label: "물가",
    eyebrow: "INFLATION PRESSURE",
    description: "물가 상승 압력이 어느 구간에 있는지 종합합니다.",
    scale: ["낮음", "안정", "높음"],
    items: [
      { key: "core_pce", weight: 0.4, short: "근원 PCE" },
      { key: "us_cpi", weight: 0.35, short: "CPI" },
      { key: "breakeven_10y", weight: 0.25, short: "기대인플레" },
    ],
    statuses: [
      { max: 30, label: "낮은 압력", tone: "normal" },
      { max: 56, label: "안정권", tone: "low" },
      { max: 76, label: "상승 경계", tone: "watch" },
      { max: 101, label: "고물가 압력", tone: "high" },
    ],
  },
  {
    key: "growth",
    label: "성장",
    eyebrow: "GROWTH MOMENTUM",
    description: "설문과 실물지표로 경기 확장 강도를 종합합니다.",
    scale: ["위축", "균형", "확장"],
    items: [
      { key: "ism_manufacturing", weight: 0.18, short: "제조 PMI" },
      { key: "ism_services", weight: 0.22, short: "서비스 PMI" },
      { key: "core_retail_sales", weight: 0.15, short: "소매판매" },
      { key: "industrial_production", weight: 0.15, short: "산업생산" },
      { key: "consumer_sentiment", weight: 0.12, short: "소비심리" },
      { key: "gdp_now", weight: 0.18, short: "GDPNow" },
    ],
    statuses: [
      { max: 30, label: "위축", tone: "high" },
      { max: 48, label: "성장 둔화", tone: "watch" },
      { max: 70, label: "완만한 확장", tone: "normal" },
      { max: 101, label: "강한 확장", tone: "low" },
    ],
  },
  {
    key: "employment",
    label: "고용",
    eyebrow: "LABOR MARKET",
    description: "해고·구인·이직 흐름으로 노동시장 강도를 종합합니다.",
    scale: ["약화", "균형", "강함"],
    items: [
      { key: "sahm_rule", weight: 0.25, short: "Sahm", invert: true },
      { key: "initial_claims", weight: 0.25, short: "실업수당", invert: true },
      { key: "jolts_ratio", weight: 0.3, short: "구인/실업자" },
      { key: "jolts_quits", weight: 0.2, short: "퇴직률" },
    ],
    statuses: [
      { max: 30, label: "고용 약화", tone: "high" },
      { max: 48, label: "고용 냉각", tone: "watch" },
      { max: 76, label: "균형·견조", tone: "normal" },
      { max: 101, label: "고용 과열", tone: "watch" },
    ],
  },
];

function indicatorBandScore(item, invert = false) {
  if (!item?.available) return null;
  const thresholds = item.thresholds || [];
  const activeIndex = thresholds.findIndex((band) => band.rangeText === item.currentRange);
  if (activeIndex < 0) return null;
  const ratio = thresholds.length > 1 ? activeIndex / (thresholds.length - 1) : 0.5;
  const score = 12 + (ratio * 76);
  return invert ? 100 - score : score;
}

function macroGaugeResult(spec) {
  const byKey = new Map(state.marketIndicators.map((item) => [item.key, item]));
  const parts = spec.items.map((definition) => {
    const item = byKey.get(definition.key);
    const score = indicatorBandScore(item, definition.invert);
    return { ...definition, item, score };
  }).filter((part) => Number.isFinite(part.score));
  if (!parts.length) return { score: null, tone: "muted", status: "계산 대기", evidence: [], parts: [], weightTotal: 0, available: 0, total: spec.items.length };
  const weightTotal = parts.reduce((sum, part) => sum + part.weight, 0);
  const score = Math.round(parts.reduce((sum, part) => sum + (part.score * part.weight), 0) / weightTotal);
  const status = spec.statuses.find((entry) => score < entry.max) || spec.statuses.at(-1);
  const evidence = parts.slice(0, 4).map((part) => `${part.short} ${formatIndicatorNumber(part.item.value)}${part.item.unit ? ` ${part.item.unit}` : ""}`);
  return { score, tone: status.tone, status: status.label, evidence, parts, weightTotal, available: parts.length, total: spec.items.length };
}

function macroGaugeHtml(spec) {
  const result = macroGaugeResult(spec);
  const selected = state.selectedMacroGauge === spec.key;
  const score = result.score ?? 50;
  const angle = -180 + (score * 1.8);
  const radians = angle * (Math.PI / 180);
  const needleX = 85 + (55 * Math.cos(radians));
  const needleY = 92 + (55 * Math.sin(radians));
  const evidence = result.evidence.length ? result.evidence.join(" · ") : "지표 데이터를 불러오는 중입니다.";
  return `<article class="macro-gauge-card ${selected ? "selected" : ""}" data-tone="${escapeHtml(result.tone)}" data-macro-gauge="${escapeHtml(spec.key)}" role="button" tabindex="0" aria-expanded="${selected}" aria-controls="macroGaugeReason" aria-label="${escapeHtml(spec.label)} 종합 상태 ${escapeHtml(result.status)}. 클릭하여 분석 근거 보기">
    <div class="macro-gauge-card-head"><div><small>${escapeHtml(spec.eyebrow)}</small><h3>${escapeHtml(spec.label)}</h3></div><strong>${escapeHtml(result.status)}</strong></div>
    <div class="macro-gauge-dial">
      <svg viewBox="0 0 170 105" role="img" aria-label="${escapeHtml(spec.label)} 종합점수 ${result.score ?? "계산 중"}">
        <path class="macro-gauge-track" d="M16 92 A69 69 0 0 1 154 92" pathLength="100"></path>
        <path class="macro-gauge-value" d="M16 92 A69 69 0 0 1 154 92" pathLength="100" stroke-dasharray="${score} 100"></path>
        <line class="macro-gauge-needle" x1="85" y1="92" x2="${needleX.toFixed(2)}" y2="${needleY.toFixed(2)}"></line>
        <circle class="macro-gauge-pivot" cx="85" cy="92" r="5"></circle>
      </svg>
      <div class="macro-gauge-score"><strong>${result.score ?? "-"}</strong><span>/ 100</span></div>
      <div class="macro-gauge-scale"><span>${escapeHtml(spec.scale[0])}</span><span>${escapeHtml(spec.scale[1])}</span><span>${escapeHtml(spec.scale[2])}</span></div>
    </div>
    <p>${escapeHtml(spec.description)}</p>
    <div class="macro-gauge-evidence"><span>${result.available}/${result.total}개 반영</span><small>${escapeHtml(evidence)}</small></div>
    <div class="macro-gauge-open-hint"><span>${selected ? "분석 근거 닫기" : "분석 근거 보기"}</span><b aria-hidden="true">${selected ? "−" : "+"}</b></div>
  </article>`;
}

function macroGaugeNarrative(spec, result) {
  if (!result.parts.length) return "현재 사용할 수 있는 지표가 없어 종합 근거를 계산하지 못했습니다.";
  const sorted = [...result.parts].sort((left, right) => right.score - left.score);
  const strongest = sorted[0];
  const weakest = sorted.at(-1);
  if (spec.key === "inflation") {
    return `${strongest.short}의 '${strongest.item.status}' 신호가 물가 압력을 가장 크게 높이고, ${weakest.short}의 '${weakest.item.status}' 신호가 이를 일부 낮췄습니다. 이 신호들을 반영해 물가 상태를 '${result.status}'로 판단했습니다.`;
  }
  const subject = spec.key === "growth" ? "경기 확장력을" : "노동시장 강도를";
  return `${strongest.short}의 '${strongest.item.status}' 신호가 ${subject} 가장 강하게 지지하지만, ${weakest.short}의 '${weakest.item.status}' 신호가 상단을 제한합니다. 전체 신호를 합산해 '${result.status}' 상태로 판단했습니다.`;
}

function macroGaugeReasoningHtml(spec) {
  const result = macroGaugeResult(spec);
  const subjectLabel = spec.key === "inflation" ? "물가가" : `${spec.label}이`;
  const rows = result.parts.map((part) => {
    const normalizedWeight = result.weightTotal ? Math.round((part.weight / result.weightTotal) * 100) : 0;
    const direction = spec.key === "inflation"
      ? "높은 구간일수록 물가압력 점수 상승"
      : part.invert
        ? "낮은 구간일수록 상태 점수 상승"
        : "높은 구간일수록 상태 점수 상승";
    return `<div class="macro-reason-row">
      <div><strong>${escapeHtml(part.short)}</strong><small>${escapeHtml(part.item.name)}</small></div>
      <div><b>${formatIndicatorNumber(part.item.value)} <small>${escapeHtml(part.item.unit || "")}</small></b><em data-tone="${escapeHtml(part.item.tone || "muted")}">${escapeHtml(part.item.status)}</em></div>
      <div><strong>${normalizedWeight}%</strong><small>${escapeHtml(direction)}</small></div>
    </div>`;
  }).join("");
  return `<section class="macro-gauge-reasoning" id="macroGaugeReason" data-tone="${escapeHtml(result.tone)}" aria-live="polite">
    <div class="macro-reason-head"><div><p class="eyebrow">WHY THIS STATUS</p><h3>${escapeHtml(subjectLabel)} ‘${escapeHtml(result.status)}’인 근거</h3></div><button type="button" data-macro-gauge-close aria-label="분석 근거 닫기">닫기</button></div>
    <div class="macro-reason-conclusion"><span>종합 판정</span><strong>${result.score ?? "-"}점 · ${escapeHtml(result.status)}</strong><p>${escapeHtml(macroGaugeNarrative(spec, result))}</p></div>
    <div class="macro-reason-labels"><span>반영 지표</span><span>현재 수치·판정</span><span>반영 비중·방향</span></div>
    <div class="macro-reason-rows">${rows || "<p>표시할 근거 데이터가 없습니다.</p>"}</div>
    <p class="macro-reason-method"><strong>계산 방법</strong> 각 지표의 현재 판정 구간을 12·37·63·88점으로 변환한 뒤 표시된 비중으로 가중 평균합니다. Sahm Rule과 실업수당처럼 낮을수록 고용에 긍정적인 지표는 점수를 반대로 계산합니다.</p>
  </section>`;
}

function macroGaugeBoardHtml() {
  const selectedSpec = MACRO_GAUGE_SPECS.find((spec) => spec.key === state.selectedMacroGauge);
  return `<section class="macro-gauge-section" aria-labelledby="macroGaugeTitle">
    <div class="macro-gauge-intro"><div><p class="eyebrow">ECONOMIC PULSE</p><h2 id="macroGaugeTitle">현재 경제 체온</h2></div><p>관련 지표의 현재 판정 구간을 가중 평균한 종합 점수입니다. 발표 주기가 다른 지표가 섞여 있으므로 방향 확인용으로 보세요.</p></div>
    <div class="macro-gauge-grid">${MACRO_GAUGE_SPECS.map(macroGaugeHtml).join("")}</div>
    ${selectedSpec ? macroGaugeReasoningHtml(selectedSpec) : ""}
  </section>`;
}

function indicatorDashboardHtml() {
  const meta = state.marketIndicatorMeta || {};
  const categoryDefinitions = [
    { value: "all", label: "전체" },
    { value: "inflation", label: "물가·기대" },
    { value: "rates", label: "금리·중앙은행" },
    { value: "growth", label: "성장·고용" },
    { value: "risk", label: "위험·유동성" },
  ];
  const categoryFor = (item) => {
    if (["core_pce", "us_cpi", "breakeven_10y"].includes(item.key)) return "inflation";
    if (["us10y", "real_policy_rate", "yield_curve", "us10y_real", "boj_rate"].includes(item.key)) return "rates";
    if ([
      "ism_manufacturing", "ism_services", "sahm_rule", "initial_claims", "jolts_ratio",
      "jolts_quits", "core_retail_sales", "industrial_production", "consumer_sentiment", "gdp_now"
    ].includes(item.key)) return "growth";
    return "risk";
  };
  const visibleIndicators = state.indicatorCategoryFilter === "all"
    ? state.marketIndicators
    : state.marketIndicators.filter((item) => categoryFor(item) === state.indicatorCategoryFilter);
  const categoryButtons = categoryDefinitions.map((category) => {
    const count = category.value === "all" ? state.marketIndicators.length : state.marketIndicators.filter((item) => categoryFor(item) === category.value).length;
    return `<button type="button" data-indicator-category="${category.value}" class="${state.indicatorCategoryFilter === category.value ? "active" : ""}">${category.label}<small>${count}</small></button>`;
  }).join("");
  let content = "";
  if (state.marketIndicatorsLoading && !state.marketIndicators.length) {
    content = `<div class="indicator-board-state">공식 출처의 최신 지표를 불러오는 중입니다…</div>`;
  } else if (state.marketIndicatorsError && !state.marketIndicators.length) {
    content = `<div class="indicator-board-state error">${escapeHtml(state.marketIndicatorsError)}</div>`;
  } else {
    content = `<div class="indicator-grid">${visibleIndicators.map(indicatorCardHtml).join("")}</div>`;
  }
  return `<section class="panel market-indicator-board">
    <div class="indicator-board-head">
      <div><p class="eyebrow">Macro &amp; Risk Monitor</p><h2>경제지표 상태판</h2><p>${escapeHtml(meta.methodology || "현재 수치가 어느 구간인지 함께 보여줍니다.")}</p></div>
      <div><span>${meta.generatedAt ? `업데이트 ${escapeHtml(formatIndicatorTimestamp(meta.generatedAt))}` : "업데이트 확인 중"}</span><button type="button" data-market-indicator-refresh ${state.marketIndicatorsLoading ? "disabled" : ""}>지표 새로고침</button></div>
    </div>
    ${macroGaugeBoardHtml()}
    <div class="indicator-category-tabs">${categoryButtons}</div>
    ${content}
  </section>`;
}

async function loadMarketIndicators(force = false) {
  if (state.marketIndicatorsLoading || (!force && state.marketIndicators.length)) return;
  state.marketIndicatorsLoading = true;
  state.marketIndicatorsError = "";
  if (state.view === "indicators") renderIndicators();
  try {
    const response = await apiFetch(`/api/market/indicators${force ? "?refresh=1" : ""}`, { cache: "no-store" });
    const payload = await response.json();
    if (!response.ok || !payload.ok) throw new Error(payload.error || `market indicators ${response.status}`);
    state.marketIndicators = payload.indicators || [];
    state.marketIndicatorMeta = { generatedAt: payload.generatedAt, methodology: payload.methodology };
  } catch (error) {
    state.marketIndicatorsError = error.message || "지표 데이터를 불러오지 못했습니다.";
  } finally {
    state.marketIndicatorsLoading = false;
    if (state.view === "indicators") renderIndicators();
  }
}

async function loadMarketChart() {
  const requestId = ++state.marketRequestId;
  const symbol = state.selectedMarketSymbol;
  const range = state.marketRange;
  const interval = state.marketInterval;
  state.marketLoading = true;
  state.marketError = "";
  renderMarket();
  try {
    await loadMarketAssets();
    const query = new URLSearchParams({ symbol, range, interval });
    const response = await apiFetch(`/api/market/chart?${query}`, { cache: "no-store" });
    const payload = await response.json();
    if (!response.ok || !payload.ok) throw new Error(payload.error || `market chart ${response.status}`);
    if (requestId !== state.marketRequestId) return;
    state.marketData = payload;
  } catch (error) {
    if (requestId !== state.marketRequestId) return;
    state.marketError = error.message || "시장 데이터를 불러오지 못했습니다.";
    state.marketData = null;
  } finally {
    if (requestId !== state.marketRequestId) return;
    state.marketLoading = false;
    if (state.view === "market") renderMarket();
  }
}

function renderMarket() {
  const data = state.marketData;
  const selected = state.marketAssets.find((item) => item.symbol === state.selectedMarketSymbol) || data?.asset;
  const assetFilterDefinitions = [{ value: "all", label: "전체" }, { value: "index", label: "지수" }, { value: "etf", label: "ETF" }, { value: "stock", label: "주식" }, { value: "other", label: "기타" }];
  const visibleMarketAssets = state.marketAssetFilter === "all" ? state.marketAssets : state.marketAssets.filter((item) => item.kind === state.marketAssetFilter);
  const assetFilterButtons = assetFilterDefinitions.map((filter) => {
    const count = filter.value === "all" ? state.marketAssets.length : state.marketAssets.filter((item) => item.kind === filter.value).length;
    return `<button type="button" data-market-filter="${filter.value}" class="${filter.value === state.marketAssetFilter ? "active" : ""}">${filter.label}<small>${count}</small></button>`;
  }).join("");
  const assetButtons = visibleMarketAssets.map((item) => `<button type="button" data-market-symbol="${escapeHtml(item.symbol)}" class="${item.symbol === state.selectedMarketSymbol ? "active" : ""}"><span>${escapeHtml(item.name)}</span><small>${escapeHtml(item.group)}</small></button>`).join("");
  const allowedFourHourRanges = ["1mo", "3mo", "6mo", "1y"];
  const rangeLabels = { "1mo": "1개월", "3mo": "3개월", "6mo": "6개월", "1y": "1년", "2y": "2년", "5y": "5년" };
  const rangeButtons = ["1mo", "3mo", "6mo", "1y", "2y", "5y"].map((value) => {
    const disabled = state.marketInterval === "4h" && !allowedFourHourRanges.includes(value);
    return `<button type="button" data-market-range="${value}" class="${value === state.marketRange ? "active" : ""}" ${disabled ? 'disabled title="4시간 봉은 최근 1년까지 지원합니다"' : ""}>${rangeLabels[value]}</button>`;
  }).join("");
  const intervalButtons = [{ value: "4h", label: "4시간" }, { value: "1d", label: "1일" }, { value: "1wk", label: "1주" }].map((item) => `<button type="button" data-market-interval="${item.value}" class="${item.value === state.marketInterval ? "active" : ""}">${item.label}</button>`).join("");
  const change = Number(data?.changePercent || 0);
  const related = marketRelatedNews(selected);
  els.content.innerHTML = `
    <section class="market-layout">
      <aside class="panel market-watchlist"><div class="feed-head"><h2>차트 종목</h2></div><div class="market-asset-tabs">${assetFilterButtons}</div><div class="market-assets">${assetButtons || `<p class="empty">종목 목록을 불러오는 중입니다.</p>`}</div></aside>
      <div class="panel market-chart-panel">
        <div class="market-toolbar">
          <div><p class="eyebrow">${escapeHtml(data ? `${data.asset.symbol} · ${data.exchange || data.asset.group}` : selected?.group || "Market")}</p><h2>${escapeHtml(data?.asset?.name || selected?.name || "시장 차트")}</h2><strong class="market-price">${data ? `${formatMarketPrice(data.price)} ${escapeHtml(data.currency)}` : "-"}</strong><span class="${change >= 0 ? "risk-low" : "risk-high"}">${data ? `${change >= 0 ? "+" : ""}${change.toFixed(2)}%` : ""}</span></div>
          <div class="market-controls">
            <div class="market-control-group"><span>봉</span><div class="market-ranges">${intervalButtons}</div></div>
            <div class="market-control-group"><span>조회 기간</span><div class="market-ranges">${rangeButtons}</div></div>
          </div>
        </div>
        <div class="market-chart-stage" data-market-chart-stage>
          <div class="market-chart-wrap" data-market-chart-wrap>${state.marketLoading ? `<div class="market-loading">시장 데이터를 불러오는 중입니다…</div>` : state.marketError ? `<div class="market-error">${escapeHtml(state.marketError)}</div>` : marketChartSvg(data)}</div>
          ${data && !state.marketLoading && !state.marketError ? marketInspectorHtml(data) : `<aside class="market-inspector market-inspector-empty">봉을 선택하면 상세 수치가 표시됩니다.</aside>`}
        </div>
        <div class="market-source"><span>기준 시각 ${escapeHtml(formatMarketDate(data?.asOf, data))}</span><span>${escapeHtml(data?.delayNotice || "지연 시세")}</span>${data?.sourceUrl ? `<a href="${escapeHtml(safeExternalUrl(data.sourceUrl))}" target="_blank" rel="noopener noreferrer">${escapeHtml(data.source)} 원문</a>` : ""}</div>
      </div>
    </section>
    ${newsFeed(`${selected?.name || "선택 종목"} 관련 뉴스`, related)}`;
  els.detail.innerHTML = detailBlock(`${selected?.name || "시장"} 해석`, "차트는 가격 움직임을 보여주며 원인을 확정하지 않습니다. 관련 뉴스와 경제 챗봇의 전달 경로 분석을 함께 확인하세요.");
  if (data && !state.marketLoading && !state.marketError) bindMarketChartInteractions(data);
  if (!state.marketLoading && !data && !state.marketError) loadMarketChart();
}

function renderIndicators() {
  els.content.innerHTML = indicatorDashboardHtml();
  els.detail.innerHTML = detailBlock("경제지표 읽는 법", "각 지표는 현재 수치와 판정 구간을 함께 보여줍니다. 한 지표만으로 결론을 내리지 말고 물가·성장·고용·금리·유동성의 상호작용을 함께 확인하세요.");
  if (!state.marketIndicatorsLoading && !state.marketIndicators.length && !state.marketIndicatorsError) loadMarketIndicators();
}

function renderAi() {
  const target = state.payload.aiStatus?.byScope?.analysis_target || {};
  const services = state.payload.aiStatus?.automationStatus || [];
  const situation = state.payload.situation || {};
  const filter = state.payload.filterImprovement || {};
  const queueEta = queueEstimateView();
  const queueEstimate = state.payload.analysisStats?.queueEstimate || {};
  const rows = services.map((service) => `
    <div class="status-row">
      <strong>${escapeHtml(service.service)}</strong>
      <p class="summary">${escapeHtml(service.detail || service.status || "")}</p>
      <span class="${service.status === "failed" || service.status === "attention" ? "risk-watch" : "risk-low"}">${escapeHtml(service.status || "-")}</span>
    </div>
  `).join("");
  els.content.innerHTML = `
    <section class="cards">
      ${smallCard("분석 완료", `${num(target.analyzed)}건`, "risk-low")}
      ${smallCard("분석 대기", `${num(target.queued)}건`, queuedCount() ? "risk-watch" : "risk-low")}
      ${smallCard("예상 완료", escapeHtml(queueEta.label), queueEta.tone)}
      ${smallCard("재개 가능 시간", escapeHtml(queueEta.resumeLabel), queueEta.tone)}
      ${smallCard("현재 판정", escapeHtml(situation.level || "-"), situation.tone || "blue")}
    </section>
    <section class="panel queue-eta-panel ${queueEstimate.conditional ? "paused" : ""}"><div><span>QUEUE ETA</span><h2>${escapeHtml(queueEta.label)}</h2><p>${escapeHtml(queueEta.note)}</p></div><dl><div><dt>재개 가능 시간</dt><dd class="${queueEta.tone}">${escapeHtml(queueEta.resumeLabel)}</dd></div><div><dt>대기</dt><dd>${num(queueEstimate.queued || 0)}건</dd></div><div><dt>최근 처리 속도</dt><dd>${num(queueEstimate.ratePerHour || 0, 1)}건/시간</dd></div><div><dt>작업 상태</dt><dd>${escapeHtml(queueEstimate.workerStatus || "-")}</dd></div></dl></section>
    <section class="section-grid">
      <div class="panel panel-pad">
        <p class="eyebrow">Situation Engine</p>
        <h2>판정 이유</h2>
        <div class="reason-list">${(situation.reasons || []).map((item) => `<p>${escapeHtml(item)}</p>`).join("") || `<p>상황 판단 데이터가 준비 중입니다.</p>`}</div>
        <div class="reason-list">${(situation.changes || []).map((item) => `<p>${escapeHtml(item)}</p>`).join("")}</div>
      </div>
      <div class="panel panel-pad">
        <p class="eyebrow">Filter Improvement</p>
        <h2>뉴스 필터 개선 상태</h2>
        <p class="summary">${escapeHtml(filter.detail || "필터 감사 기록이 아직 없습니다.")}</p>
        <div class="reason-list">${(filter.recommendations || []).map((item) => `<p>${escapeHtml(item)}</p>`).join("")}</div>
      </div>
    </section>
    <section class="panel"><div class="feed-head"><h2>자동화 상태</h2><div class="tabs"><span class="active">실시간</span><span>누적</span></div></div>${rows || `<p class="empty">자동화 상태 데이터가 없습니다.</p>`}</section>
  `;
  els.detail.innerHTML = detailBlock("자동화 해석", "누적 오류 숫자보다 현재 status와 detail을 우선 보면 됩니다. filter attention은 고장이라기보다 뉴스 필터 개선 신호입니다.");
}

function renderEvaluation() {
  const evaluation = state.payload.economicEvaluation || {};
  const feedback = evaluation.feedback || {};
  const forecasts = evaluation.forecasts || {};
  const weaknessLabels = { substantive_answer: "답변 깊이", maps_key_variables: "핵심 변수 지도", has_variable_interactions: "변수 상호작용", multiple_mechanisms: "메커니즘", has_counterarguments: "반대 논리", has_scenario_analysis: "조건별 시나리오", has_turning_conditions: "결론 전환 조건", has_news_evidence: "뉴스 근거", has_knowledge: "경제 지식", states_scope_assumptions: "분석 범위·전제", states_uncertainty: "불확실성", scenario_is_calibrated: "시나리오 보정", multiple_assumptions: "가정 검토" };
  const weaknesses = (evaluation.weaknesses || []).map((item) => `<div class="weakness-row"><span>${escapeHtml(weaknessLabels[item.key] || item.key)}</span><strong>${num(item.count)}회</strong></div>`).join("");
  const improvementQueue = (evaluation.improvementQueue || []).map((item) => `<div class="improvement-row ${escapeHtml(item.severity)}"><span>${escapeHtml(item.severity)}</span><div><strong>${escapeHtml(compact(item.question || item.type, 85))}</strong><p>${escapeHtml(item.detail)}</p></div></div>`).join("");
  const rows = (evaluation.recent || []).map((item) => `<div class="evaluation-row">
    <span class="evaluation-score ${Number(item.score || 0) >= 80 ? "risk-low" : Number(item.score || 0) >= 60 ? "risk-watch" : "risk-high"}">${num(item.score, 1)}</span>
    <span><strong>${escapeHtml(compact(item.question, 90))}</strong><small>${escapeHtml(item.provider || "-")} · ${escapeHtml(item.model || "-")} · ${escapeHtml(item.createdAt || "")}</small></span>
    <em>${item.rating === 1 ? "도움됨" : item.rating === -1 ? "개선 필요" : "미평가"}</em>
  </div>`).join("");
  els.content.innerHTML = `
    <section class="cards">
      ${smallCard("누적 분석", `${num(evaluation.analysisCount)}건`, "blue")}
      ${smallCard("평균 품질점수", `${num(evaluation.averageScore, 1)}점`, Number(evaluation.averageScore || 0) >= 80 ? "risk-low" : "risk-watch")}
      ${smallCard("도움됨 비율", `${num(feedback.helpfulRate, 1)}%`, "risk-low")}
      ${smallCard("평가 완료 예측", `${num(forecasts.evaluated)}건`, "blue")}
    </section>
    <section class="section-grid">
      <div class="panel panel-pad"><p class="eyebrow">Quality Rubric</p><h2>자동 품질 채점</h2><p class="summary">답변 구조 25점, 근거 사용 25점, 경제 추론 30점, 불확실성 보정 20점으로 평가합니다.</p></div>
      <div class="panel panel-pad"><p class="eyebrow">Forecast Audit</p><h2>30일 결과 검증</h2><div class="risk-row"><span>평가 대기</span><strong>${num(forecasts.open)}건</strong></div><div class="risk-row"><span>평균 기준 오차</span><strong>${num(forecasts.meanAbsoluteError, 2)}%</strong></div></div>
    </section>
    <section class="section-grid">
      <div class="panel panel-pad"><p class="eyebrow">Repeated Weaknesses</p><h2>반복 약점</h2>${weaknesses || `<p class="empty">아직 발견된 반복 약점이 없습니다.</p>`}</div>
      <div class="panel panel-pad"><p class="eyebrow">Improvement Queue</p><h2>개선 대기 항목</h2>${improvementQueue || `<p class="empty">현재 개선 대기 항목이 없습니다.</p>`}</div>
    </section>
    <section class="panel"><div class="feed-head"><h2>최근 경제 분석</h2><div class="tabs"><span class="active">최근 10건</span></div></div>${rows || `<p class="empty">저장된 경제 분석이 아직 없습니다. 챗봇에 질문하면 자동으로 기록됩니다.</p>`}</section>`;
  els.detail.innerHTML = detailBlock("평가 기준", "점수가 높아도 경제적 결론이 참이라는 뜻은 아닙니다. 구조와 근거 사용을 자동 점검하고, 실제 정확도는 30일 뒤 결과 검증으로 따로 측정합니다.");
}

function renderChatMessage(message) {
  if (message.role === "user") {
    return `<article class="chat-message user"><div class="chat-role">나</div><p>${escapeHtml(message.content)}</p></article>`;
  }
  if (message.error) {
    return `<article class="chat-message assistant error"><div class="chat-role">오류</div><p>${escapeHtml(message.content)}</p></article>`;
  }
  const sources = (message.sources || []).map((source) => `<a class="chat-source" href="${escapeHtml(safeExternalUrl(source.url))}" target="_blank" rel="noopener noreferrer">${escapeHtml(source.ref)} · ${escapeHtml(source.date || "")} · ${escapeHtml(source.title)}</a>`).join("");
  const knowledge = (message.knowledge || []).map((item) => `<div class="knowledge-card"><strong>${escapeHtml(item.title)}</strong><span>${escapeHtml(item.domain)} · 신뢰도 ${Math.round(Number(item.confidence || 0) * 100)}%</span></div>`).join("");
  const calc = message.calculations;
  const calculations = calc?.sample_size ? `<div class="calculation-grid">
    <div><span>검색 표본</span><strong>${num(calc.sample_size)}건</strong></div>
    <div><span>평균 영향도</span><strong>${num(calc.average_impact, 1)}</strong></div>
    <div><span>고위험 비중</span><strong>${num(calc.high_risk_share, 1)}%</strong></div>
    <div><span>표본 기간</span><strong>${escapeHtml(calc.period?.start || "-")} ~ ${escapeHtml(calc.period?.end || "-")}</strong></div>
  </div>` : "";
  const macroSeries = (message.macroSeries || []).map((item) => `<a class="macro-row" href="${escapeHtml(safeExternalUrl(item.source_url))}" target="_blank" rel="noopener noreferrer">
    <span><strong>${escapeHtml(item.title)}</strong><small>${escapeHtml(item.series_id)} · ${escapeHtml(item.date)}</small></span>
    <span class="macro-value">${num(item.value, 2)} ${escapeHtml(item.unit)}<small>1개월 ${item.change_1m_pct == null ? "-" : `${num(item.change_1m_pct, 2)}%`}</small></span>
  </a>`).join("");
  const scenario = message.scenarios;
  const scenarioWeights = (scenario?.scenarios || []).map((item) => `<div class="scenario-weight ${escapeHtml(item.key)}"><span>${escapeHtml(item.label)}</span><strong>${num(item.probability, 1)}%</strong></div>`).join("");
  const scenarioIndicators = (scenario?.indicators || []).map((item) => `<div class="scenario-row"><strong>${escapeHtml(item.title)}</strong><span>${num(item.favorable, 2)}</span><span>${num(item.base, 2)}</span><span>${num(item.adverse, 2)} ${escapeHtml(item.unit)}</span></div>`).join("");
  const list = (title, values) => values?.length ? `<div class="chat-analysis"><strong>${title}</strong><ul>${values.map((value) => `<li>${escapeHtml(value)}</li>`).join("")}</ul></div>` : "";
  return `<article class="chat-message assistant">
    <div class="chat-role">경제 분석 AI</div>
    <p class="chat-answer">${escapeHtml(message.content)}</p>
    ${list("분석 범위·전제", message.assumptions)}
    ${list("핵심 변수 지도", message.keyVariables)}
    ${list("변수 상호작용", message.variableInteractions)}
    ${list("경제 메커니즘", message.economicMechanisms)}
    ${list("반대 논리", message.counterarguments)}
    ${list("조건별 시나리오", message.scenarioAnalysis)}
    ${list("결론이 바뀌는 조건", message.turningConditions)}
    ${message.uncertainty ? `<div class="chat-uncertainty"><strong>불확실성</strong><p>${escapeHtml(message.uncertainty)}</p></div>` : ""}
    ${calculations ? `<div class="chat-calculations"><strong>계산 도구 결과</strong>${calculations}<small>질문과 관련해 검색된 뉴스 표본의 기술통계입니다.</small></div>` : ""}
    ${macroSeries ? `<div class="chat-macro"><strong>공식 거시 시계열</strong>${macroSeries}</div>` : ""}
    ${scenarioIndicators ? `<div class="chat-scenario"><strong>시나리오 비교</strong><div class="scenario-weights">${scenarioWeights}</div><div class="scenario-head"><span>지표</span><span>우호</span><span>기준</span><span>위험</span></div>${scenarioIndicators}<small>${escapeHtml(scenario.disclaimer || "")}</small></div>` : ""}
    ${knowledge ? `<div class="chat-knowledge"><strong>사용한 경제 지식</strong>${knowledge}</div>` : ""}
    ${sources ? `<div class="chat-sources"><strong>DB 근거</strong>${sources}</div>` : ""}
    ${message.analysisId ? `<div class="chat-feedback"><span>이 분석이 유용했나요?</span><button type="button" data-feedback="1" data-analysis-id="${message.analysisId}" class="${message.rating === 1 ? "active" : ""}">도움됨</button><button type="button" data-feedback="-1" data-analysis-id="${message.analysisId}" class="${message.rating === -1 ? "active" : ""}">개선 필요</button></div>` : ""}
  </article>`;
}

const calendarCategoryLabels = {
  central_bank: "통화정책",
  inflation: "물가",
  labor: "고용",
  growth: "성장",
  earnings: "실적",
  market: "시장",
};

function filteredCalendarEvents() {
  return (state.payload.calendarEvents || []).filter((item) =>
    (state.calendarCountry === "all" || item.country === state.calendarCountry) &&
    (state.calendarCategory === "all" || item.category === state.calendarCategory) &&
    (state.calendarImportance === "all" || item.importance === state.calendarImportance)
  );
}

function calendarEventDetail(item) {
  if (!item) return detailBlock("일정 상세", "캘린더에서 일정을 선택하면 발표 수치와 출처가 표시됩니다.");
  const dateText = new Intl.DateTimeFormat("ko-KR", {
    timeZone: "Asia/Seoul", month: "long", day: "numeric", weekday: "short", hour: "2-digit", minute: "2-digit",
  }).format(new Date(item.scheduledAt));
  const displayValue = (label, content, role = "") => `
    <div class="calendar-value ${role}"><span>${label}</span><strong>${content == null || content === "" ? "—" : escapeHtml(content)}</strong></div>`;
  return `
    <div class="calendar-detail-head">
      <span class="country-badge ${item.country.toLowerCase()}">${item.country === "KR" ? "한국" : item.country === "US" ? "미국" : "글로벌"}</span>
      <span class="importance-dot ${item.importance}">${item.importance === "high" ? "중요" : item.importance === "medium" ? "보통" : "참고"}</span>
    </div>
    <h2>${escapeHtml(item.title)}</h2>
    <p class="calendar-detail-time">${escapeHtml(dateText)} · 한국시간</p>
    <div class="calendar-values">
      ${displayValue("실제치", item.actual && `${item.actual}${item.unit || ""}`, "actual")}
      ${displayValue("컨센서스", item.forecast && `${item.forecast}${item.unit || ""}`)}
      ${displayValue("이전치", item.previous && `${item.previous}${item.unit || ""}`)}
    </div>
    <div class="detail-section"><div class="detail-title">기준 기간</div><p>${escapeHtml(item.period || "—")}</p></div>
    <div class="detail-section"><div class="detail-title">메모</div><p>${escapeHtml(item.notes || "발표 후 실제 수치가 업데이트됩니다.")}</p></div>
    <a class="source-link" href="${escapeHtml(safeExternalUrl(item.sourceUrl))}" target="_blank" rel="noopener noreferrer">${escapeHtml(item.sourceName)}에서 확인 ↗</a>
    <p class="source-status">${item.confirmed ? "공식 일정 확인됨" : "예상 일정"}</p>`;
}

function renderCalendar() {
  const [year, month] = state.calendarMonth.split("-").map(Number);
  const firstDay = new Date(year, month - 1, 1);
  const lastDate = new Date(year, month, 0).getDate();
  const events = filteredCalendarEvents();
  const cells = [];
  for (let index = 0; index < firstDay.getDay(); index += 1) cells.push(`<div class="calendar-day outside"></div>`);
  for (let day = 1; day <= lastDate; day += 1) {
    const iso = `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
    const dayEvents = events.filter((item) => String(item.scheduledAt).slice(0, 10) === iso);
    const eventButtons = dayEvents.map((item) => {
      const time = new Date(item.scheduledAt).toLocaleTimeString("ko-KR", { timeZone: "Asia/Seoul", hour: "2-digit", minute: "2-digit", hour12: false });
      return `<button type="button" class="calendar-event ${item.country.toLowerCase()} ${item.importance} ${item.id === state.selectedCalendarEventId ? "selected" : ""}" data-calendar-event="${escapeHtml(item.id)}"><span>${time}</span>${escapeHtml(item.title)}</button>`;
    }).join("");
    cells.push(`<div class="calendar-day ${iso === "2026-07-22" ? "today" : ""}"><span class="day-number">${day}</span><div class="day-events">${eventButtons}</div></div>`);
  }
  const selected = (state.payload.calendarEvents || []).find((item) => item.id === state.selectedCalendarEventId) || events[0];
  if (selected) state.selectedCalendarEventId = selected.id;
  els.content.innerHTML = `
    <section class="calendar-toolbar panel-pad panel">
      <div class="calendar-month-nav"><button type="button" data-calendar-month="prev" aria-label="이전 달">‹</button><strong>${year}년 ${month}월</strong><button type="button" data-calendar-month="next" aria-label="다음 달">›</button></div>
      <div class="calendar-filters">
        <select id="calendarCountry" aria-label="국가"><option value="all">전체 국가</option><option value="US" ${state.calendarCountry === "US" ? "selected" : ""}>미국</option><option value="KR" ${state.calendarCountry === "KR" ? "selected" : ""}>한국</option></select>
        <select id="calendarCategory" aria-label="유형"><option value="all">전체 유형</option>${Object.entries(calendarCategoryLabels).map(([key, label]) => `<option value="${key}" ${state.calendarCategory === key ? "selected" : ""}>${label}</option>`).join("")}</select>
        <select id="calendarImportance" aria-label="중요도"><option value="all">전체 중요도</option><option value="high" ${state.calendarImportance === "high" ? "selected" : ""}>중요</option><option value="medium" ${state.calendarImportance === "medium" ? "selected" : ""}>보통</option></select>
      </div>
    </section>
    <section class="panel calendar-shell">
      <div class="calendar-weekdays">${["일", "월", "화", "수", "목", "금", "토"].map((day) => `<span>${day}</span>`).join("")}</div>
      <div class="calendar-grid">${cells.join("")}</div>
    </section>`;
  els.detail.innerHTML = calendarEventDetail(selected);
}

function calendarDateKey(date) {
  const parts = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Seoul", year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(date);
  const values = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return `${values.year}-${values.month}-${values.day}`;
}

function renderCalendarV2() {
  const events = filteredCalendarEvents();
  const todayKey = calendarDateKey(new Date());
  const [year, month] = state.calendarMonth.split("-").map(Number);
  let rangeLabel = `${year}년 ${month}월`;
  let calendarBody = "";

  if (state.calendarMode === "month") {
    const firstDay = new Date(year, month - 1, 1);
    const lastDate = new Date(year, month, 0).getDate();
    const cells = [];
    for (let index = 0; index < firstDay.getDay(); index += 1) cells.push(`<div class="calendar-day outside"></div>`);
    for (let day = 1; day <= lastDate; day += 1) {
      const iso = `${year}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
      const dayEvents = events.filter((item) => String(item.scheduledAt).slice(0, 10) === iso);
      const eventButtons = dayEvents.map((item) => {
        const time = new Date(item.scheduledAt).toLocaleTimeString("ko-KR", { timeZone: "Asia/Seoul", hour: "2-digit", minute: "2-digit", hour12: false });
        return `<button type="button" class="calendar-event ${item.country.toLowerCase()} ${item.importance} ${item.id === state.selectedCalendarEventId ? "selected" : ""}" data-calendar-event="${escapeHtml(item.id)}"><span>${time}</span>${escapeHtml(item.title)}</button>`;
      }).join("");
      cells.push(`<div class="calendar-day ${iso === todayKey ? "today" : ""}"><span class="day-number">${day}</span><div class="day-events">${eventButtons}</div></div>`);
    }
    calendarBody = `<section class="panel calendar-shell"><div class="calendar-weekdays">${["일", "월", "화", "수", "목", "금", "토"].map((day) => `<span>${day}</span>`).join("")}</div><div class="calendar-grid">${cells.join("")}</div></section>`;
  } else {
    const anchor = new Date();
    anchor.setHours(12, 0, 0, 0);
    const mondayOffset = (anchor.getDay() + 6) % 7;
    anchor.setDate(anchor.getDate() - mondayOffset + state.calendarWeekOffset * 7);
    const days = Array.from({ length: 7 }, (_, index) => {
      const date = new Date(anchor);
      date.setDate(anchor.getDate() + index);
      return date;
    });
    const end = days[6];
    rangeLabel = `${anchor.getMonth() + 1}월 ${anchor.getDate()}일 – ${end.getMonth() + 1}월 ${end.getDate()}일`;
    const dayColumns = days.map((date) => {
      const iso = calendarDateKey(date);
      const dayEvents = events.filter((item) => String(item.scheduledAt).slice(0, 10) === iso);
      const rows = dayEvents.length ? dayEvents.map((item) => {
        const time = new Date(item.scheduledAt).toLocaleTimeString("ko-KR", { timeZone: "Asia/Seoul", hour: "2-digit", minute: "2-digit", hour12: false });
        return `<button type="button" class="calendar-week-event ${item.country.toLowerCase()} ${item.importance} ${item.id === state.selectedCalendarEventId ? "selected" : ""}" data-calendar-event="${escapeHtml(item.id)}">
          <span class="calendar-week-time">${time}</span><b>${escapeHtml(item.title)}</b><small>${escapeHtml(item.country)} · ${escapeHtml(calendarCategoryLabels[item.category] || item.category)}</small>
        </button>`;
      }).join("") : `<p class="calendar-week-empty">예정 일정 없음</p>`;
      return `<section class="calendar-week-day ${iso === todayKey ? "today" : ""}"><header><span>${["일", "월", "화", "수", "목", "금", "토"][date.getDay()]}</span><strong>${date.getDate()}</strong><em>${dayEvents.length}</em></header><div>${rows}</div></section>`;
    }).join("");
    calendarBody = `<section class="calendar-week-board">${dayColumns}</section>`;
  }

  const visibleIds = new Set(events.map((item) => item.id));
  const selected = (state.payload.calendarEvents || []).find((item) => item.id === state.selectedCalendarEventId && visibleIds.has(item.id)) || events[0];
  if (selected) state.selectedCalendarEventId = selected.id;
  els.content.innerHTML = `
    <section class="calendar-toolbar panel-pad panel">
      <div class="calendar-month-nav"><button type="button" data-calendar-step="prev" aria-label="이전 기간">‹</button><strong>${rangeLabel}</strong><button type="button" data-calendar-step="next" aria-label="다음 기간">›</button></div>
      <div class="calendar-toolbar-right">
        <div class="calendar-mode-toggle"><button type="button" data-calendar-mode="week" class="${state.calendarMode === "week" ? "active" : ""}">주간</button><button type="button" data-calendar-mode="month" class="${state.calendarMode === "month" ? "active" : ""}">월간</button></div>
        <div class="calendar-filters">
          <select id="calendarCountry" aria-label="국가"><option value="all">전체 국가</option><option value="US" ${state.calendarCountry === "US" ? "selected" : ""}>미국</option><option value="KR" ${state.calendarCountry === "KR" ? "selected" : ""}>한국</option></select>
          <select id="calendarCategory" aria-label="유형"><option value="all">전체 유형</option>${Object.entries(calendarCategoryLabels).map(([key, label]) => `<option value="${key}" ${state.calendarCategory === key ? "selected" : ""}>${label}</option>`).join("")}</select>
          <select id="calendarImportance" aria-label="중요도"><option value="all">전체 중요도</option><option value="high" ${state.calendarImportance === "high" ? "selected" : ""}>중요</option><option value="medium" ${state.calendarImportance === "medium" ? "selected" : ""}>보통</option></select>
        </div>
      </div>
    </section>${calendarBody}`;
  els.detail.innerHTML = calendarEventDetail(selected);
}

function renderChat() {
  const messages = state.chatMessages.map(renderChatMessage).join("");
  els.content.innerHTML = `
    <section class="panel chat-shell">
      <div class="chat-intro">
        <p class="eyebrow">Economic Reasoning Agent</p>
        <h2>데이터를 근거로 경제적으로 생각합니다</h2>
        <p>수요·공급·정책·금융시장·지정학 변수의 상호작용과 2차 효과를 함께 검토합니다.</p>
        <div class="chat-prompts">
          <button type="button" data-chat-prompt="최근 뉴스에서 시장의 가장 큰 하방 위험은 무엇이야?">가장 큰 하방 위험</button>
          <button type="button" data-chat-prompt="현재 상황에서 금리와 환율이 자산시장에 미칠 영향을 시나리오별로 분석해줘.">금리·환율 시나리오</button>
          <button type="button" data-chat-prompt="최근 고영향 뉴스들의 공통 원인과 반대 가설을 찾아줘.">공통 원인과 반대 가설</button>
        </div>
      </div>
      <div class="chat-log" id="chatLog">${messages || `<p class="empty">위 예시를 누르거나 경제 질문을 입력해 보세요.</p>`}</div>
      <form class="chat-form" id="chatForm">
        <textarea id="chatInput" rows="3" maxlength="2000" placeholder="예: 유가 상승이 한국 경제에 미치는 1차·2차 효과를 분석해줘" ${state.chatLoading ? "disabled" : ""}></textarea>
        <button type="submit" ${state.chatLoading ? "disabled" : ""}>${state.chatLoading ? "분석 중…" : "분석하기"}</button>
      </form>
    </section>`;
  els.detail.innerHTML = detailBlock("경제적 사고 프레임", "핵심 변수를 원인·매개·증폭·상쇄·피드백으로 연결하고 기준·우호·위험 조건에서 결론이 어떻게 달라지는지 확인합니다.");
  requestAnimationFrame(() => {
    const log = document.querySelector("#chatLog");
    if (log) log.scrollTop = log.scrollHeight;
  });
}

async function askEconomicChat(question) {
  const cleaned = String(question || "").trim();
  if (!cleaned || state.chatLoading) return;
  const history = state.chatMessages.filter((message) => !message.error).slice(-6).map((message) => ({ role: message.role, content: message.content }));
  state.chatMessages.push({ role: "user", content: cleaned });
  state.chatLoading = true;
  renderChat();
  try {
    const response = await apiFetch("/api/economic-chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: cleaned, history }),
    });
    const payload = await response.json();
    if (!response.ok || !payload.ok) throw new Error(payload.error || `chat ${response.status}`);
    state.chatMessages.push({ role: "assistant", content: payload.answer, assumptions: payload.assumptions, keyVariables: payload.key_variables, variableInteractions: payload.variable_interactions, economicMechanisms: payload.economic_mechanisms, counterarguments: payload.counterarguments, scenarioAnalysis: payload.scenario_analysis, turningConditions: payload.turning_conditions, uncertainty: payload.uncertainty, sources: payload.sources, knowledge: payload.knowledge, calculations: payload.calculations, macroSeries: payload.macro_series, scenarios: payload.scenarios, analysisId: payload.analysis_id });
  } catch (error) {
    state.chatMessages.push({ role: "assistant", content: error.message || "분석 요청에 실패했습니다.", error: true });
  } finally {
    state.chatLoading = false;
    renderChat();
  }
}

function detailBlock(title, text) {
  return `
    <h2>${escapeHtml(ui(title))}</h2>
    <div class="detail-section"><div class="detail-title">${escapeHtml(ui("AI 상황 판단"))}</div><p>${escapeHtml(ui(text))}</p></div>
    <div class="detail-section"><div class="detail-title">${escapeHtml(ui("관찰 포인트"))}</div>
      <div class="risk-row"><span>${escapeHtml(ui("핵심 지역"))}</span><strong>${escapeHtml(localizeRegion(topRegionName()))}</strong></div>
      <div class="risk-row"><span>${escapeHtml(ui("분석 대기"))}</span><strong>${state.lang === "en" ? formatCount(queuedCount()) : `${num(queuedCount())}건`}</strong></div>
      <div class="risk-row"><span>${escapeHtml(ui("총 뉴스"))}</span><strong>${state.lang === "en" ? formatCount(state.payload.newsItems.length) : `${num(state.payload.newsItems.length)}건`}</strong></div>
    </div>
  `;
}

function render() {
  const meta = localizedViewMeta();
  const [title, status] = meta[state.view] || meta.home;
  els.pageTitle.textContent = title;
  els.pageStatus.textContent = status;
  document.querySelectorAll("#nav [data-view]").forEach((button) => button.classList.toggle("active", button.dataset.view === state.view));

  const renderers = {
    home: renderHomeV2,
    dashboard: renderDashboard,
    daily: renderNewsHub,
    flows: renderFlows,
    regions: renderRegions,
    assets: renderAssetHub,
    watchlist: renderWatchlist,
    market: renderMarket,
    indicators: renderIndicators,
    calendar: renderCalendarV2,
    chat: renderChat,
    evaluation: renderEvaluation,
    ai: renderAi,
  };
  (renderers[state.view] || renderHome)();
  renderChrome();
  ensureEnglishTranslations();
}

function updateLanguageChrome() {
  document.documentElement.lang = state.lang;
  document.body.dataset.lang = state.lang;
  document.title = t("brand");
  if (els.brandTitle) els.brandTitle.textContent = t("brand");
  if (els.brandSubtitle) els.brandSubtitle.textContent = t("subtitle");
  if (els.updateBoxLabel) els.updateBoxLabel.textContent = t("updateLabel");
  if (els.languageToggle) {
    els.languageToggle.textContent = t("englishToggle");
    els.languageToggle.setAttribute("aria-label", state.lang === "ko" ? "Switch to English" : "한국어로 전환");
  }
  document.querySelectorAll("#nav [data-view]").forEach((button) => {
    const koNav = { watchlist:"관심 자산", home:"홈", dashboard:"시장 상황", daily:"뉴스·근거", flows:"이슈 흐름", regions:"지역 리스크", assets:"자산 허브", market:"시장 차트", indicators:"경제지표", calendar:"경제 캘린더", chat:"경제 AI", evaluation:"분석 평가", ai:"시스템 현황" };
    const label = state.lang === "ko" ? koNav[button.dataset.view] : (button.dataset.view === "watchlist" ? "Watchlist" : I18N.en.nav[button.dataset.view]);
    if (label) button.textContent = label;
  });
  if (!els.manualUpdateButton.disabled) {
    els.manualUpdateButton.textContent = t("refresh");
  }
}

function renderFreshnessNotice() {
  const latest = state.payload.meta?.latestNewsAt;
  const date = latest ? new Date(latest) : null;
  const ageHours = date && !Number.isNaN(date.getTime()) ? (Date.now() - date.getTime()) / 3_600_000 : null;
  const current = document.querySelector("#freshnessNotice");
  if (ageHours === null || ageHours <= 36) {
    current?.remove();
    return;
  }
  const days = Math.max(1, Math.floor(ageHours / 24));
  const updating = ["queued", "running", "collecting"].includes(String(state.payload.meta?.manualUpdate?.status || "").toLowerCase());
  const message = state.lang === "en" ? `Latest collected news is ${days} day${days === 1 ? "" : "s"} old.` : `수집된 최신 뉴스가 ${days}일 전 자료입니다.`;
  const action = updating ? (state.lang === "en" ? "Update in progress" : "업데이트 진행 중") : (state.lang === "en" ? "Update now" : "지금 업데이트");
  const html = `<section class="freshness-notice" id="freshnessNotice"><span><b>${state.lang === "en" ? "Data freshness" : "데이터 최신성"}</b>${message}</span><button type="button" data-freshness-refresh="1" ${updating ? "disabled" : ""}>${action}</button></section>`;
  if (current) current.outerHTML = html;
  else els.content.insertAdjacentHTML("afterbegin", html);
}

function renderChrome() {
  const meta = state.payload.meta || {};
  const manual = meta.manualUpdate || {};
  const latest = meta.lastUpdatedAt || meta.latestNewsAt;
  updateLanguageChrome();
  els.lastUpdatedAt.textContent = formatUpdateTime(latest);
  els.manualUpdateStatus.textContent = manual.status || t("waiting");
  els.sideQueued.textContent = num(queuedCount());
  els.sideRegion.textContent = localizeRegion(topRegionName());
  renderFreshnessNotice();
  applyEnglishStaticText(document.body);
}

function clearAuthSession(message = "") {
  if (state.authExpiryTimer) clearTimeout(state.authExpiryTimer);
  state.authExpiryTimer = null;
  state.authExpiresAt = null;
  state.authRequired = true;
  state.authenticated = false;
  state.payload = {
    dailyBriefings: {}, newsItems: [], issues: [], assetViews: [], regionViews: [],
    aiStatus: {}, analysisStats: {}, economicEvaluation: {}, calendarEvents: [],
    sourceDocuments: [], meta: {},
  };
  state.marketAssets = [];
  state.marketIndicators = [];
  state.marketData = null;
  state.chatMessages = [];
  state.deepAnalysisById = {};
  state.translationsById = {};
  renderLogin(message);
}

function scheduleAuthExpiry(expiresAt) {
  if (state.authExpiryTimer) clearTimeout(state.authExpiryTimer);
  state.authExpiryTimer = null;
  state.authExpiresAt = expiresAt || null;
  if (!expiresAt) return;
  const remainingMs = new Date(expiresAt).getTime() - Date.now();
  if (!Number.isFinite(remainingMs) || remainingMs <= 0) {
    clearAuthSession("로그인 후 6시간이 지나 다시 인증이 필요합니다.");
    return;
  }
  state.authExpiryTimer = setTimeout(
    () => clearAuthSession("로그인 후 6시간이 지나 다시 인증이 필요합니다."),
    remainingMs,
  );
}

async function apiFetch(url, options = {}) {
  const response = await fetch(url, { ...options, credentials: "same-origin" });
  if (response.status === 401) {
    clearAuthSession("로그인이 만료되었거나 비밀번호가 필요합니다.");
    throw new Error("authentication required");
  }
  return response;
}

async function checkAuthStatus() {
  const response = await fetch("/api/auth/status", { cache: "no-store", credentials: "same-origin" });
  if (!response.ok) throw new Error(`auth ${response.status}`);
  const payload = await response.json();
  state.authRequired = Boolean(payload.authRequired);
  state.authenticated = !state.authRequired || Boolean(payload.authenticated);
  if (state.authenticated) scheduleAuthExpiry(payload.expiresAt);
  return state.authenticated;
}

function renderLogin(message = "") {
  document.body.classList.add("auth-locked");
  els.content.innerHTML = `
    <section class="auth-gate">
      <div class="auth-card">
        <img class="auth-logo" src="./assets/eminai_primary_logo.png" alt="EMINAI by SH" />
        <div class="auth-product-name">WATCH · ECONOMIC INTELLIGENCE</div>
        <p>접근 비밀번호를 입력하세요.</p>
        <form id="authForm">
          <input id="authPassword" type="password" autocomplete="current-password" placeholder="비밀번호" />
          <button type="submit">입장</button>
        </form>
        <small>${message || state.authError || ""}</small>
      </div>
    </section>
  `;
  els.detail.innerHTML = "";
  els.pageTitle.textContent = "에미나이 Watch";
  els.pageStatus.textContent = "Protected dashboard";
  els.manualUpdateStatus.textContent = "locked";
  els.lastUpdatedAt.textContent = "-";
  els.sideQueued.textContent = "-";
  els.sideRegion.textContent = "-";
}

async function submitAuth(password) {
  state.authError = "";
  const response = await fetch("/api/auth/login", {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password }),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok || !payload.ok) {
    state.authError = "비밀번호가 맞지 않습니다.";
    renderLogin();
    return false;
  }
  scheduleAuthExpiry(payload.expiresAt);
  state.authRequired = Boolean(payload.authRequired);
  state.authenticated = true;
  document.body.classList.remove("auth-locked");
  await loadData();
  render();
  return true;
}

async function logout() {
  try {
    await fetch("/api/auth/logout", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    });
  } finally {
    clearAuthSession("로그아웃되었습니다.");
  }
}

async function loadData() {
  const response = await apiFetch("/api/bootstrap", { cache: "no-store" });
  if (!response.ok) throw new Error(`bootstrap ${response.status}`);
  state.payload = await response.json();
  if (!state.selectedNewsId) state.selectedNewsId = highImpactNews(1)[0]?.id || latestNews()[0]?.id || null;
}

async function requestManualUpdate() {
  els.manualUpdateButton.disabled = true;
  els.manualUpdateButton.textContent = t("updating");
  try {
    const response = await apiFetch("/api/manual-update", { method: "POST" });
    if (!response.ok) throw new Error(`manual update ${response.status}`);
    await loadData();
    render();
  } finally {
    els.manualUpdateButton.disabled = false;
    els.manualUpdateButton.textContent = t("refresh");
  }
}

async function requestDeepAnalysis(newsId, refresh = false) {
  state.deepAnalysisLoadingId = newsId;
  state.deepAnalysisError = "";
  els.detail.innerHTML = detailForNews(selectedNews());
  try {
    const response = await apiFetch("/api/news/deep-analysis", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: newsId, refresh }),
    });
    const payload = await response.json();
    if (!response.ok || !payload.ok) throw new Error(payload.error || `deep analysis ${response.status}`);
    if (payload.deepAnalysis) state.deepAnalysisById[newsId] = payload.deepAnalysis;
  } catch (error) {
    state.deepAnalysisError = String(error.message || error);
  } finally {
    state.deepAnalysisLoadingId = null;
    els.detail.innerHTML = detailForNews(selectedNews());
  }
}

async function requestEnglishTranslations(ids) {
  const missing = ids.filter((id) => id && !state.translationsById[id]);
  if (!missing.length || state.translationLoading) return;
  state.translationLoading = true;
  state.translationError = "";
  render();
  try {
    const cachedResponse = await apiFetch(`/api/news/translations?ids=${encodeURIComponent(missing.join(","))}`, { cache: "no-store" });
    if (cachedResponse.ok) {
      const cachedPayload = await cachedResponse.json();
      for (const item of cachedPayload.translations || []) {
        state.translationsById[item.newsItemId] = item;
      }
      render();
    }
    const stillMissing = missing.filter((id) => !state.translationsById[id]);
    if (!stillMissing.length) return;
    const response = await apiFetch("/api/news/translations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ids: stillMissing, limitNew: 3 }),
    });
    const payload = await response.json();
    if (!response.ok || !payload.ok) throw new Error(payload.error || `translations ${response.status}`);
    for (const item of payload.translations || []) {
      state.translationsById[item.newsItemId] = item;
    }
  } catch (error) {
    state.translationError = String(error.message || error);
  } finally {
    state.translationLoading = false;
    render();
  }
}

function toggleMacroGauge(key) {
  state.selectedMacroGauge = state.selectedMacroGauge === key ? null : key;
  renderIndicators();
}

els.languageToggle?.addEventListener("click", () => {
  state.lang = state.lang === "ko" ? "en" : "ko";
  localStorage.setItem("eminai_lang", state.lang);
  render();
});

els.nav.addEventListener("click", (event) => {
  const button = event.target.closest("[data-view]");
  if (!button) return;
  state.view = button.dataset.view;
  render();
});

function handleNewsHubFilterClick(event) {
  const newsSource = event.target.closest("[data-news-source]");
  if (newsSource) {
    state.newsHubSource = newsSource.dataset.newsSource;
    renderNewsHub();
    return true;
  }

  const newsImpact = event.target.closest("[data-news-impact]");
  if (newsImpact) {
    state.newsHubImpact = newsImpact.dataset.newsImpact;
    renderNewsHub();
    return true;
  }

  const newsRegion = event.target.closest("[data-news-region]");
  if (newsRegion) {
    state.newsHubRegion = newsRegion.dataset.newsRegion;
    renderNewsHub();
    return true;
  }

  const newsTopic = event.target.closest("[data-news-topic]");
  if (newsTopic) {
    state.newsHubTopic = newsTopic.dataset.newsTopic;
    renderNewsHub();
    return true;
  }

  const newsSort = event.target.closest("[data-news-sort]");
  if (newsSort) {
    state.newsHubSort = newsSort.dataset.newsSort;
    renderNewsHub();
    return true;
  }

  const newsReset = event.target.closest("[data-news-reset]");
  if (newsReset) {
    state.newsHubQuery = "";
    state.newsHubSource = "all";
    state.newsHubImpact = "all";
    state.newsHubRegion = "all";
    state.newsHubTopic = "all";
    state.newsHubSort = "latest";
    state.newsHubDate = "all";
    renderNewsHub();
    return true;
  }

  return false;
}

els.detail.addEventListener("click", (event) => {
  const watchButton = event.target.closest("[data-watch-asset]");
  if (watchButton) {
    toggleWatchedAsset(watchButton.dataset.watchAsset);
    state.view === "watchlist" ? renderWatchlist() : renderAssetHub();
    return;
  }
  if (handleNewsHubFilterClick(event)) return;

  const freshnessRefresh = event.target.closest("[data-freshness-refresh]");
  if (freshnessRefresh) {
    els.manualUpdateButton?.click();
    return;
  }

  const menu = event.target.closest("[data-go]");
  if (menu) {
    state.view = menu.dataset.go;
    render();
    return;
  }
  const deepButton = event.target.closest("[data-deep-analysis-id]");
  if (!deepButton) return;
  const newsId = Number(deepButton.dataset.deepAnalysisId);
  requestDeepAnalysis(newsId, deepButton.dataset.refreshDeep === "1");
});

els.content.addEventListener("click", (event) => {
  if (handleNewsHubFilterClick(event)) return;

  const watchButton = event.target.closest("[data-watch-asset]");
  if (watchButton) {
    toggleWatchedAsset(watchButton.dataset.watchAsset);
    state.view === "watchlist" ? renderWatchlist() : renderAssetHub();
    return;
  }

  const watchChart = event.target.closest("[data-watch-chart]");
  if (watchChart) {
    state.selectedMarketSymbol = watchChart.dataset.watchChart;
    state.view = "market";
    render();
    return;
  }
  const calendarEvent = event.target.closest("[data-calendar-event]");
  if (calendarEvent) {
    state.selectedCalendarEventId = calendarEvent.dataset.calendarEvent;
    const item = (state.payload.calendarEvents || []).find((entry) => entry.id === state.selectedCalendarEventId);
    els.detail.innerHTML = calendarEventDetail(item);
    document.querySelectorAll("[data-calendar-event]").forEach((button) => button.classList.toggle("selected", button.dataset.calendarEvent === state.selectedCalendarEventId));
    return;
  }

  const calendarMode = event.target.closest("[data-calendar-mode]");
  if (calendarMode) {
    state.calendarMode = calendarMode.dataset.calendarMode;
    state.selectedCalendarEventId = null;
    renderCalendarV2();
    return;
  }

  const calendarStep = event.target.closest("[data-calendar-step]");
  if (calendarStep) {
    const offset = calendarStep.dataset.calendarStep === "next" ? 1 : -1;
    if (state.calendarMode === "week") {
      state.calendarWeekOffset += offset;
    } else {
      const [year, month] = state.calendarMonth.split("-").map(Number);
      const nextMonth = new Date(year, month - 1 + offset, 1);
      state.calendarMonth = `${nextMonth.getFullYear()}-${String(nextMonth.getMonth() + 1).padStart(2, "0")}`;
    }
    state.selectedCalendarEventId = null;
    renderCalendarV2();
    return;
  }

  const calendarMonth = event.target.closest("[data-calendar-month]");
  if (calendarMonth) {
    const [year, month] = state.calendarMonth.split("-").map(Number);
    const offset = calendarMonth.dataset.calendarMonth === "next" ? 1 : -1;
    const nextMonth = new Date(year, month - 1 + offset, 1);
    state.calendarMonth = `${nextMonth.getFullYear()}-${String(nextMonth.getMonth() + 1).padStart(2, "0")}`;
    state.selectedCalendarEventId = null;
    renderCalendarV2();
    return;
  }

  const marketZoom = event.target.closest("[data-market-zoom]");
  if (marketZoom && state.marketData) {
    zoomMarketChart(state.marketData, marketZoom.dataset.marketZoom);
    return;
  }

  const macroGaugeClose = event.target.closest("[data-macro-gauge-close]");
  if (macroGaugeClose) {
    state.selectedMacroGauge = null;
    renderIndicators();
    return;
  }

  const macroGauge = event.target.closest("[data-macro-gauge]");
  if (macroGauge) {
    toggleMacroGauge(macroGauge.dataset.macroGauge);
    return;
  }

  const indicatorRefresh = event.target.closest("[data-market-indicator-refresh]");
  if (indicatorRefresh) {
    loadMarketIndicators(true);
    return;
  }

  const indicatorCategory = event.target.closest("[data-indicator-category]");
  if (indicatorCategory) {
    state.indicatorCategoryFilter = indicatorCategory.dataset.indicatorCategory;
    renderIndicators();
    return;
  }

  const marketFilter = event.target.closest("[data-market-filter]");
  if (marketFilter) {
    state.marketAssetFilter = marketFilter.dataset.marketFilter;
    const visibleAssets = state.marketAssetFilter === "all" ? state.marketAssets : state.marketAssets.filter((item) => item.kind === state.marketAssetFilter);
    if (visibleAssets.length && !visibleAssets.some((item) => item.symbol === state.selectedMarketSymbol)) {
      state.marketRequestId += 1;
      state.marketLoading = false;
      state.selectedMarketSymbol = visibleAssets[0].symbol;
      state.marketData = null;
      state.marketError = "";
      resetMarketViewport();
    }
    renderMarket();
    return;
  }

  const marketSymbol = event.target.closest("[data-market-symbol]");
  if (marketSymbol) {
    state.marketRequestId += 1;
    state.marketLoading = false;
    state.selectedMarketSymbol = marketSymbol.dataset.marketSymbol;
    state.marketData = null;
    state.marketError = "";
    resetMarketViewport();
    if (state.view !== "market") {
      state.view = "market";
      render();
    } else {
      renderMarket();
    }
    return;
  }

  const marketInterval = event.target.closest("[data-market-interval]");
  if (marketInterval) {
    state.marketRequestId += 1;
    state.marketLoading = false;
    state.marketInterval = marketInterval.dataset.marketInterval;
    if (state.marketInterval === "4h" && !["1mo", "3mo", "6mo", "1y"].includes(state.marketRange)) state.marketRange = "1y";
    state.marketData = null;
    state.marketError = "";
    resetMarketViewport();
    renderMarket();
    return;
  }

  const marketRange = event.target.closest("[data-market-range]");
  if (marketRange) {
    state.marketRequestId += 1;
    state.marketLoading = false;
    state.marketRange = marketRange.dataset.marketRange;
    state.marketData = null;
    state.marketError = "";
    resetMarketViewport();
    renderMarket();
    return;
  }

  const feedback = event.target.closest("[data-feedback]");
  if (feedback) {
    submitEconomicFeedback(Number(feedback.dataset.analysisId), Number(feedback.dataset.feedback));
    return;
  }

  const menu = event.target.closest("[data-go]");
  if (menu) {
    state.view = menu.dataset.go;
    render();
    return;
  }

  const newsButton = event.target.closest("[data-news-id]");
  if (newsButton) {
    state.selectedNewsId = Number(newsButton.dataset.newsId);
    if (state.lang === "en") requestEnglishTranslations([state.selectedNewsId]);
    if (newsButton.dataset.view) {
      state.view = newsButton.dataset.view;
      render();
      return;
    }
    els.detail.innerHTML = detailForNews(selectedNews());
    return;
  }

  const region = event.target.closest("[data-region]");
  if (region) {
    state.selectedRegion = region.dataset.region;
    renderRegions();
    return;
  }

  const asset = event.target.closest("[data-asset]");
  if (asset) {
    state.selectedAsset = asset.dataset.asset;
    const selectedHubAsset = assetHubItems().find((item) => item.name === state.selectedAsset);
    if (selectedHubAsset?.symbol) state.selectedMarketSymbol = selectedHubAsset.symbol;
    if (asset.dataset.openAsset) state.view = "assets";
    renderAssetHub();
    return;
  }

  const assetFilter = event.target.closest("[data-asset-filter]");
  if (assetFilter) {
    state.assetHubFilter = assetFilter.dataset.assetFilter;
    renderAssetHub();
  }
});

els.content.addEventListener("input", (event) => {
  if (event.target.id === "assetHubSearch") {
    state.assetHubSearch = event.target.value;
    renderAssetHub();
    const input = document.querySelector("#assetHubSearch");
    input?.focus();
    input?.setSelectionRange(state.assetHubSearch.length, state.assetHubSearch.length);
    return;
  }
  if (event.target.id === "newsHubSearch") {
    state.newsHubQuery = event.target.value;
    renderNewsHub();
    const input = document.querySelector("#newsHubSearch");
    input?.focus();
    input?.setSelectionRange(state.newsHubQuery.length, state.newsHubQuery.length);
  }
});

els.content.addEventListener("change", (event) => {
  if (event.target.id !== "newsHubDate") return;
  state.newsHubDate = event.target.value;
  renderNewsHub();
});

els.content.addEventListener("error", (event) => {
  if (!event.target.matches?.(".asset-logo img")) return;
  const fallbackSrc = event.target.dataset.fallbackSrc;
  if (fallbackSrc && event.target.src !== fallbackSrc && event.target.dataset.fallbackTried !== "1") {
    event.target.dataset.fallbackTried = "1";
    event.target.src = fallbackSrc;
    return;
  }
  event.target.hidden = true;
  if (event.target.nextElementSibling) event.target.nextElementSibling.hidden = false;
}, true);

els.content.addEventListener("keydown", (event) => {
  const macroGauge = event.target.closest("[data-macro-gauge]");
  if (!macroGauge || !["Enter", " "].includes(event.key)) return;
  event.preventDefault();
  toggleMacroGauge(macroGauge.dataset.macroGauge);
});

els.content.addEventListener("submit", (event) => {
  if (event.target.id === "authForm") {
    event.preventDefault();
    const input = event.target.querySelector("#authPassword");
    submitAuth(input?.value || "").catch((error) => {
      state.authError = String(error.message || error);
      renderLogin();
    });
    return;
  }
  if (event.target.id !== "chatForm") return;
  event.preventDefault();
  const input = event.target.querySelector("#chatInput");
  askEconomicChat(input?.value);
});

async function submitEconomicFeedback(analysisId, rating) {
  if (!analysisId || ![-1, 1].includes(rating)) return;
  const response = await apiFetch("/api/economic-chat/feedback", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ analysisId, rating }),
  });
  if (!response.ok) return;
  const message = state.chatMessages.find((item) => item.analysisId === analysisId);
  if (message) message.rating = rating;
  renderChat();
}

els.content.addEventListener("change", (event) => {
  if (["calendarCountry", "calendarCategory", "calendarImportance"].includes(event.target.id)) {
    if (event.target.id === "calendarCountry") state.calendarCountry = event.target.value;
    if (event.target.id === "calendarCategory") state.calendarCategory = event.target.value;
    if (event.target.id === "calendarImportance") state.calendarImportance = event.target.value;
    state.selectedCalendarEventId = null;
    renderCalendarV2();
    return;
  }
  if (event.target.id === "dateSelect") {
    state.selectedDate = event.target.value;
    state.selectedNewsId = newsForDate(state.selectedDate)[0]?.id || state.selectedNewsId;
    renderDaily();
  }
});

els.manualUpdateButton.addEventListener("click", () => {
  requestManualUpdate().catch((error) => {
    console.info(error);
    els.manualUpdateStatus.textContent = "실패";
    els.manualUpdateButton.disabled = false;
    els.manualUpdateButton.textContent = "새로고침";
  });
});

document.querySelector("#logoutButton")?.addEventListener("click", () => {
  logout().catch((error) => console.info(error));
});

/*
loadData()
  .catch((error) => {
    console.info(error);
    els.content.innerHTML = `<p class="empty">API 데이터를 불러오지 못했습니다. 서버 상태를 확인해 주세요.</p>`;
    els.detail.innerHTML = detailBlock("연결 대기", "데이터 API가 준비되면 자동화 결과가 표시됩니다.");
  })
  .finally(render);
*/

checkAuthStatus()
  .then((authenticated) => {
    if (!authenticated) {
      renderLogin();
      return null;
    }
    document.body.classList.remove("auth-locked");
    return loadData();
  })
  .catch((error) => {
    console.info(error);
    if (state.authRequired && !state.authenticated) {
      renderLogin();
      return;
    }
    els.content.innerHTML = `<p class="empty">API 데이터를 불러오지 못했습니다. 서버 상태를 확인해 주세요.</p>`;
    els.detail.innerHTML = detailBlock("연결 대기", "데이터 API가 준비되면 자동으로 결과가 표시됩니다.");
  })
  .finally(() => {
    if (!state.authRequired || state.authenticated) render();
  });
