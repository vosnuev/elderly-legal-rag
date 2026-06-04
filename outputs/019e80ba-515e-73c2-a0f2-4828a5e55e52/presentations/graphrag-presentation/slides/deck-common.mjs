import path from "node:path";

const W = 1280;
const H = 720;

const P = {
  bg: "#F8F4F0",
  paper: "#FFFFFF",
  ink: "#151126",
  muted: "#6F6878",
  line: "#DDD0C7",
  brown: "#6C2E12",
  brownSoft: "#F7ECE4",
  teal: "#0F766E",
  tealSoft: "#DDF6F1",
  purple: "#6655E8",
  purpleSoft: "#EEEAFE",
  blue: "#2563EB",
  blueSoft: "#E8F0FF",
  green: "#0F9F6E",
  greenSoft: "#E4F8EF",
  amber: "#C77700",
  amberSoft: "#FFF1D6",
  rose: "#BE3455",
  roseSoft: "#FFE7EF",
  dark: "#17151D",
};

function A(ctx) {
  return ctx.artifact;
}

function ts(ctx, value) {
  return A(ctx).textStyle(`${value}; family: Arial`);
}

function fill(ctx, color) {
  return A(ctx).paint(color);
}

function stroke(ctx, value) {
  return A(ctx).stroke(value);
}

function txt(ctx, value, x, y, w, h, style) {
  return A(ctx).text(value, {
    position: { left: x, top: y },
    width: w,
    height: h,
    style: ts(ctx, style),
  });
}

function rect(ctx, x, y, w, h, color, opts = {}) {
  return A(ctx).shape({
    position: { left: x, top: y },
    width: w,
    height: h,
    fill: fill(ctx, color),
    line: opts.line === false ? stroke(ctx, "none") : stroke(ctx, `${opts.lineWidth ?? 1}px ${opts.lineColor ?? P.line}`),
    borderRadius: opts.radius ?? 14,
  });
}

function circle(ctx, x, y, d, color, opts = {}) {
  return A(ctx).shape({
    geometry: "ellipse",
    position: { left: x, top: y },
    width: d,
    height: d,
    fill: fill(ctx, color),
    line: opts.line === false ? stroke(ctx, "none") : stroke(ctx, `${opts.lineWidth ?? 1}px ${opts.lineColor ?? P.line}`),
  });
}

function hline(ctx, x, y, w, color = P.line, weight = 2) {
  return rect(ctx, x, y, w, weight, color, { line: false, radius: 0 });
}

function vline(ctx, x, y, h, color = P.line, weight = 2) {
  return rect(ctx, x, y, weight, h, color, { line: false, radius: 0 });
}

function arrow(ctx, x, y, color = P.brown) {
  return txt(ctx, "→", x, y, 32, 24, `font-size: 20px; font-weight: 800; color: ${color}; alignment: center`);
}

function pill(ctx, label, x, y, w, color = P.brown, soft = P.brownSoft) {
  return [
    rect(ctx, x, y, w, 30, soft, { lineColor: color, radius: 15 }),
    txt(ctx, label, x + 12, y + 8, w - 24, 16, `font-size: 10.5px; font-weight: 800; color: ${color}; alignment: center`),
  ];
}

function node(ctx, label, sub, x, y, w, h, color = P.teal, soft = P.tealSoft) {
  return [
    rect(ctx, x, y, w, h, soft, { lineColor: color, radius: 12 }),
    txt(ctx, label, x + 16, y + 14, w - 32, 26, `font-size: 16px; font-weight: 800; color: ${P.ink}; leading: 1.05`),
    txt(ctx, sub, x + 16, y + 44, w - 32, Math.max(22, h - 52), `font-size: 12px; color: ${P.muted}; leading: 1.15`),
  ];
}

function smallNode(ctx, label, x, y, w, color, soft) {
  return [
    rect(ctx, x, y, w, 48, soft, { lineColor: color, radius: 10 }),
    txt(ctx, label, x + 10, y + 16, w - 20, 16, `font-size: 12.5px; font-weight: 800; color: ${P.ink}; alignment: center`),
  ];
}

function compose(slide, ctx, children) {
  slide.compose(A(ctx).layers({ width: W, height: H }, children.flat(8).filter(Boolean)));
}

function header(ctx, slide, eyebrow, title, subtitle, no) {
  slide.background.fill = { color: P.bg };
  return [
    txt(ctx, eyebrow.toUpperCase(), 56, 28, 760, 18, `font-size: 10px; font-weight: 800; color: ${P.brown}; leading: 1`),
    txt(ctx, title, 56, 54, 1010, 66, `font-size: 30px; font-weight: 800; color: ${P.ink}; leading: 1.04`),
    txt(ctx, subtitle, 58, 120, 930, 26, `font-size: 12.5px; color: ${P.muted}; leading: 1.15`),
    txt(ctx, String(no).padStart(2, "0"), 1186, 48, 38, 18, `font-size: 12px; font-weight: 800; color: ${P.brown}; alignment: right`),
    hline(ctx, 56, 152, 1168, "#E5DCD5", 1),
  ];
}

function metric(ctx, value, label, x, y, w, color) {
  return [
    rect(ctx, x, y, w, 78, P.paper, { lineColor: "#E2D8D0", radius: 10 }),
    txt(ctx, value, x + 18, y + 14, w - 36, 30, `font-size: 25px; font-weight: 800; color: ${color}`),
    txt(ctx, label, x + 18, y + 48, w - 36, 18, `font-size: 10.5px; color: ${P.muted}`),
  ];
}

function slide01(presentation, ctx) {
  const slide = presentation.slides.add();
  slide.background.fill = { color: P.dark };
  compose(slide, ctx, [
    rect(ctx, 0, 0, 1280, 720, P.dark, { line: false, radius: 0 }),
    rect(ctx, 772, 0, 508, 720, "#F4EDE7", { line: false, radius: 0 }),
    txt(ctx, "검수 가능한 GraphRAG 서비스", 68, 74, 640, 126, `font-size: 54px; font-weight: 800; color: #FFFFFF; leading: 1.04`),
    txt(ctx, "Streaming Frontend, LLM Runtime Backend, GraphRAG Knowledge Layer를 분리한 법령/조례 RAG 시스템", 72, 214, 600, 60, `font-size: 19px; color: #D8D2DC; leading: 1.18`),
    ...pill(ctx, "Streaming FE → Main Backend → MCP → GraphRAG → Memgraph", 72, 320, 560, P.green, "#122E28"),
    txt(ctx, "핵심 주장", 72, 424, 120, 18, `font-size: 11px; font-weight: 800; color: #C9B6A8`),
    txt(ctx, "RAG system은 knowledge layer이고, Main Backend는 answer generation runtime이다. 두 영역은 MCP read-only tool boundary로 분리했다.", 72, 452, 620, 96, `font-size: 20px; color: #FFFFFF; leading: 1.18`),
    ...metric(ctx, "40.81%", "TOON 전처리 전체 토큰 절감률", 832, 100, 320, P.brown),
    ...metric(ctx, "360", "대표/엣지 질문 테스트 케이스", 832, 202, 320, P.purple),
    ...metric(ctx, "reviewable", "candidate first, edge later", 832, 304, 320, P.teal),
    ...metric(ctx, "read-only MCP", "최종 backend graph query boundary", 832, 406, 320, P.blue),
    txt(ctx, "SKN28 3rd 1Team · GraphRAG Presentation v4", 72, 650, 500, 18, `font-size: 12px; color: #9D96A8`),
  ]);
  return slide;
}

function slide02(presentation, ctx) {
  const slide = presentation.slides.add();
  compose(slide, ctx, [
    ...header(ctx, slide, "Problem framing", "Why vector-only RAG is not enough", "법령/조례 도메인은 의미 유사도뿐 아니라 조항 간 관계, 예외, 근거 검수가 필요하다.", 2),
    rect(ctx, 72, 188, 500, 392, P.paper, { lineColor: "#E2D7CF", radius: 18 }),
    txt(ctx, "일반 vector RAG", 106, 220, 260, 28, `font-size: 23px; font-weight: 800; color: ${P.ink}`),
    ...node(ctx, "Chunk", "문서를 조각으로 나눔", 112, 282, 150, 86, P.brown, P.brownSoft),
    arrow(ctx, 280, 313),
    ...node(ctx, "Embedding", "벡터화 후 top-k 검색", 326, 282, 170, 86, P.brown, P.brownSoft),
    arrow(ctx, 234, 400),
    ...node(ctx, "Answer", "근거/관계 검수는 약함", 202, 438, 210, 90, P.rose, P.roseSoft),
    txt(ctx, "유사 문장은 찾지만 조문 간 관계와 예외의 타당성을 검수하기 어렵다.", 110, 540, 390, 28, `font-size: 13.5px; color: ${P.muted}; leading: 1.2`),
    rect(ctx, 700, 188, 500, 392, P.paper, { lineColor: "#D8D0FF", radius: 18 }),
    txt(ctx, "이번 GraphRAG", 734, 220, 260, 28, `font-size: 23px; font-weight: 800; color: ${P.ink}`),
    ...node(ctx, "Chunk + Embedding", "의미 단위 chunk와 vector 저장", 746, 276, 200, 82, P.teal, P.tealSoft),
    arrow(ctx, 956, 306, P.purple),
    ...node(ctx, "Graph Traverse", "문서/조항/후보 관계 탐색", 994, 276, 170, 82, P.purple, P.purpleSoft),
    arrow(ctx, 856, 392, P.purple),
    ...node(ctx, "Candidate", "edge가 아닌 검수 artifact", 746, 430, 180, 82, P.amber, P.amberSoft),
    arrow(ctx, 942, 460, P.purple),
    ...node(ctx, "Human Review", "승인 후보만 edge 확정", 990, 430, 180, 82, P.green, P.greenSoft),
    txt(ctx, "LLM은 제안하고, 사용자가 검수하며, DB에는 검증된 관계만 반영한다.", 746, 540, 390, 28, `font-size: 13.5px; color: ${P.muted}; leading: 1.2`),
  ]);
  return slide;
}

function slide03(presentation, ctx) {
  const slide = presentation.slides.add();
  const originalW = 560;
  const toonW = 332;
  compose(slide, ctx, [
    ...header(ctx, slide, "Data & preprocessing", "law.go.kr JSON을 TOON으로 바꿔 전체 토큰 40.81% 절감", "원본 API 구조를 보존하되 LLM 입력 비용을 줄이기 위해 JSON 문법 토큰을 제거했다.", 3),
    ...node(ctx, "law.go.kr API", "lawSearch.do / lawService.do / target=ordin", 78, 188, 240, 84, P.blue, P.blueSoft),
    arrow(ctx, 334, 218),
    ...node(ctx, "JSON 원본", "법령/조례 원천 구조 저장", 390, 188, 210, 84, P.brown, P.brownSoft),
    arrow(ctx, 616, 218),
    ...node(ctx, "TOON 변환", "LLM-friendly text representation", 672, 188, 230, 84, P.teal, P.tealSoft),
    arrow(ctx, 918, 218),
    ...node(ctx, "RAG 입력", "chunking agent가 읽는 전처리 문서", 974, 188, 220, 84, P.green, P.greenSoft),
    txt(ctx, "Token compression proof", 80, 340, 360, 28, `font-size: 24px; font-weight: 800; color: ${P.ink}`),
    txt(ctx, "320,991", 80, 386, 112, 28, `font-size: 24px; font-weight: 800; color: ${P.brown}`),
    rect(ctx, 210, 390, originalW, 22, "#C49A82", { line: false, radius: 11 }),
    txt(ctx, "원본 JSON tokens", 210, 420, 180, 18, `font-size: 12px; color: ${P.muted}`),
    txt(ctx, "189,997", 80, 466, 112, 28, `font-size: 24px; font-weight: 800; color: ${P.teal}`),
    rect(ctx, 210, 470, toonW, 22, P.teal, { line: false, radius: 11 }),
    txt(ctx, "TOON tokens", 210, 500, 160, 18, `font-size: 12px; color: ${P.muted}`),
    rect(ctx, 790, 352, 360, 170, P.paper, { lineColor: "#E2D8D0", radius: 16 }),
    txt(ctx, "절감 토큰", 824, 384, 120, 18, `font-size: 12px; font-weight: 800; color: ${P.muted}`),
    txt(ctx, "130,994", 824, 408, 180, 42, `font-size: 38px; font-weight: 800; color: ${P.green}`),
    txt(ctx, "전체 합계 기준 절감률 40.81%. 문서별 평균이 아니라 전체 token sum 기준이다.", 824, 466, 280, 38, `font-size: 14px; color: ${P.muted}; leading: 1.2`),
    txt(ctx, "근거: rag/code_reference 수집/전처리 코드, rag/RAG_PREPROCESSED_DATA/README.md", 80, 626, 780, 18, `font-size: 11px; color: ${P.muted}`),
  ]);
  return slide;
}

function slide04(presentation, ctx) {
  const slide = presentation.slides.add();
  compose(slide, ctx, [
    ...header(ctx, slide, "End-to-end architecture", "최종 서비스는 Frontend, LLM Runtime, GraphRAG Knowledge Layer로 분리", "사용자가 보는 stream UX와 graph를 구축하는 pipeline을 같은 runtime에 섞지 않았다.", 4),
    ...node(ctx, "User", "질문 입력", 58, 286, 120, 76, P.brown, P.brownSoft),
    arrow(ctx, 188, 310),
    ...node(ctx, "Streaming Frontend", "token/event stream 렌더링", 230, 270, 200, 108, P.blue, P.blueSoft),
    arrow(ctx, 448, 310),
    ...node(ctx, "Main Backend", "LLM chat runtime\nprompt · session · stream", 492, 250, 220, 148, P.purple, P.purpleSoft),
    ...node(ctx, "LLM Provider", "answer synthesis", 500, 458, 200, 76, P.purple, "#F6F2FF"),
    vline(ctx, 604, 405, 46, P.purple, 3),
    arrow(ctx, 730, 310, P.purple),
    ...node(ctx, "MCP Client", "tool call boundary", 774, 286, 150, 76, P.amber, P.amberSoft),
    arrow(ctx, 942, 310, P.amber),
    ...node(ctx, "RAG MCP Server", "read-only graph tools", 984, 272, 190, 104, P.teal, P.tealSoft),
    vline(ctx, 1080, 386, 46, P.teal, 3),
    ...node(ctx, "Memgraph", "verified knowledge graph", 984, 444, 190, 84, P.green, P.greenSoft),
    rect(ctx, 246, 566, 778, 52, "#FFF9F3", { lineColor: "#E2C8B0", radius: 14 }),
    txt(ctx, "GraphRAG build path는 별도: RAG Admin FE → RAG Backend API → Task Queue → Worker → RelationshipCandidate → Human Review → Memgraph", 276, 584, 718, 18, `font-size: 14px; font-weight: 800; color: ${P.brown}; alignment: center`),
  ]);
  return slide;
}

function slide05(presentation, ctx) {
  const slide = presentation.slides.add();
  const cols = [
    ["Streaming Frontend", "사용자 질문 입력, token delta 렌더링, tool status/citation 표시", "Presentation layer", P.blue, P.blueSoft],
    ["Main Backend", "session/context 구성, prompt policy, LLM 호출, MCP tool routing", "Answer generation runtime", P.purple, P.purpleSoft],
    ["GraphRAG System", "문서 업로드, graph build, review queue, memory, read-only MCP 제공", "Knowledge construction layer", P.teal, P.tealSoft],
  ];
  compose(slide, ctx, [
    ...header(ctx, slide, "Three system boundaries", "각 영역은 서로 다른 책임을 가진다", "최종 사용자 응답 runtime과 knowledge graph 구축 runtime을 분리한 것이 핵심 설계다.", 5),
    ...cols.map((c, i) => {
      const x = 70 + i * 395;
      return [
        rect(ctx, x, 206, 340, 312, c[4], { lineColor: c[3], radius: 20 }),
        circle(ctx, x + 28, 238, 42, c[3], { line: false }),
        txt(ctx, String(i + 1), x + 41, 250, 16, 16, `font-size: 12px; font-weight: 800; color: #FFFFFF; alignment: center`),
        txt(ctx, c[0], x + 84, 232, 220, 26, `font-size: 22px; font-weight: 800; color: ${P.ink}`),
        txt(ctx, c[1], x + 34, 302, 270, 82, `font-size: 18px; color: ${P.ink}; leading: 1.15`),
        hline(ctx, x + 34, 420, 250, c[3], 3),
        txt(ctx, c[2], x + 34, 448, 250, 22, `font-size: 14px; font-weight: 800; color: ${c[3]}`),
      ];
    }),
    txt(ctx, "한 줄 정리: RAG system은 knowledge layer이고, Main Backend는 answer generation runtime이다.", 160, 594, 960, 28, `font-size: 19px; font-weight: 800; color: ${P.ink}; alignment: center`),
  ]);
  return slide;
}

function slide06(presentation, ctx) {
  const slide = presentation.slides.add();
  const events = ["message.started", "token.delta", "tool.started", "tool.result", "citation.ready", "message.completed"];
  compose(slide, ctx, [
    ...header(ctx, slide, "Streaming frontend runtime", "Frontend는 RAG 내부를 직접 실행하지 않고 backend stream을 UX로 변환", "사용자는 긴 답변을 기다리는 대신 token, tool status, evidence event를 순차적으로 본다.", 6),
    ...node(ctx, "Question Input", "사용자가 질문 입력", 82, 302, 170, 76, P.brown, P.brownSoft),
    arrow(ctx, 270, 326),
    ...node(ctx, "Stream Request", "chat stream endpoint 호출", 318, 302, 180, 76, P.blue, P.blueSoft),
    arrow(ctx, 516, 326),
    ...node(ctx, "Main Backend", "agent loop 실행", 566, 302, 170, 76, P.purple, P.purpleSoft),
    arrow(ctx, 754, 326),
    ...node(ctx, "Event Builder", "stream event serialize", 810, 302, 180, 76, P.green, P.greenSoft),
    arrow(ctx, 1008, 326),
    ...node(ctx, "Live UI", "token/tool/citation 렌더링", 1058, 302, 170, 76, P.teal, P.tealSoft),
    rect(ctx, 168, 464, 944, 82, P.paper, { lineColor: "#E2D8D0", radius: 18 }),
    ...events.map((e, i) => {
      const x = 200 + i * 145;
      return [
        ...pill(ctx, e, x, 490, 130, i < 2 ? P.blue : i < 4 ? P.purple : P.green, i < 2 ? P.blueSoft : i < 4 ? P.purpleSoft : P.greenSoft),
      ];
    }),
    txt(ctx, "Frontend slide에서는 RAG 구조를 설명하지 않고, stream lifecycle과 사용자 경험만 설명한다.", 234, 594, 812, 24, `font-size: 17px; font-weight: 700; color: ${P.muted}; alignment: center`),
  ]);
  return slide;
}

async function slide07(presentation, ctx) {
  const slide = presentation.slides.add();
  const flowImage = path.join(process.cwd(), "backend/flow.PNG");
  compose(slide, ctx, [
    ...header(ctx, slide, "Main backend: LLM chat runtime", "최종 답변 생성은 backend가 담당하고 RAG는 MCP tool로 호출된다", "backend는 prompt, session context, tool routing, LLM provider 호출, stream response를 조율한다.", 7),
    rect(ctx, 62, 190, 500, 370, P.paper, { lineColor: "#E2D8D0", radius: 18 }),
    txt(ctx, "Runtime responsibilities", 96, 220, 280, 24, `font-size: 22px; font-weight: 800; color: ${P.ink}`),
    ...smallNode(ctx, "Chat Stream API", 104, 282, 180, P.blue, P.blueSoft),
    ...smallNode(ctx, "Session / Conversation Context", 334, 282, 180, P.purple, P.purpleSoft),
    ...smallNode(ctx, "Prompt + Policy", 104, 370, 180, P.brown, P.brownSoft),
    ...smallNode(ctx, "LLM Agent Orchestrator", 334, 370, 180, P.purple, P.purpleSoft),
    ...smallNode(ctx, "MCP Tool Router", 104, 458, 180, P.amber, P.amberSoft),
    ...smallNode(ctx, "Stream Event Builder", 334, 458, 180, P.green, P.greenSoft),
    arrow(ctx, 294, 294, P.purple),
    arrow(ctx, 294, 382, P.purple),
    arrow(ctx, 294, 470, P.purple),
    rect(ctx, 602, 190, 610, 370, "#FAF9F7", { lineColor: "#D8CBC2", radius: 18 }),
    txt(ctx, "실제 backend flow reference", 632, 214, 240, 20, `font-size: 15px; font-weight: 800; color: ${P.brown}`),
    txt(ctx, "source: backend/flow.PNG", 980, 216, 170, 16, `font-size: 10.5px; color: ${P.muted}; alignment: right`),
    rect(ctx, 618, 246, 578, 294, "#FFFFFF", { lineColor: "#E5DCD5", radius: 12 }),
    txt(ctx, "image loading...", 840, 374, 140, 18, `font-size: 13px; color: ${P.muted}; alignment: center`),
  ]);
  await ctx.addImage(slide, { path: flowImage, left: 622, top: 250, width: 570, height: 286, fit: "contain", alt: "backend flow diagram" });
  return slide;
}

function slide08(presentation, ctx) {
  const slide = presentation.slides.add();
  compose(slide, ctx, [
    ...header(ctx, slide, "Backend to RAG via MCP", "MCP는 answer runtime과 GraphRAG system 사이의 read-only boundary", "Main Backend는 graph를 수정하지 않고, RAG MCP server의 조회 tool만 호출한다.", 8),
    ...node(ctx, "Main Backend", "Answer Runtime\nLLM agent · prompt · stream", 82, 284, 230, 118, P.purple, P.purpleSoft),
    arrow(ctx, 336, 322, P.purple),
    ...node(ctx, "MCP Client", "tool call adapter", 390, 304, 160, 76, P.amber, P.amberSoft),
    arrow(ctx, 572, 322, P.amber),
    rect(ctx, 628, 216, 260, 248, P.paper, { lineColor: P.blue, radius: 18 }),
    txt(ctx, "RAG MCP Server", 660, 248, 200, 24, `font-size: 22px; font-weight: 800; color: ${P.ink}`),
    ...pill(ctx, "schema_read", 664, 298, 130, P.blue, P.blueSoft),
    ...pill(ctx, "text_search", 664, 342, 130, P.blue, P.blueSoft),
    ...pill(ctx, "vector_search", 664, 386, 130, P.blue, P.blueSoft),
    ...pill(ctx, "graph_traverse", 664, 430, 144, P.blue, P.blueSoft),
    arrow(ctx, 906, 322, P.blue),
    ...node(ctx, "Memgraph", "Document · Chunk · Edge · Memory", 964, 286, 220, 112, P.teal, P.tealSoft),
    ...node(ctx, "GraphRAG Builder", "Ingest / Review / Memory pipeline만 approved graph write 수행", 474, 516, 330, 80, P.green, P.greenSoft),
    txt(ctx, "no write from answer runtime", 958, 440, 220, 18, `font-size: 13px; font-weight: 800; color: ${P.rose}; alignment: center`),
    rect(ctx, 214, 604, 850, 42, "#FFF9F3", { lineColor: "#E2C8B0", radius: 14 }),
    txt(ctx, "이 구조 덕분에 외부 agent나 최종 backend가 같은 graph를 안정적으로 조회할 수 있다.", 246, 616, 790, 18, `font-size: 15px; font-weight: 800; color: ${P.brown}; alignment: center`),
  ]);
  return slide;
}

async function slide09(presentation, ctx) {
  const slide = presentation.slides.add();
  const graphPath = path.join(process.cwd(), "presentation/ppt/assets/memgraph-lab-graph-cluster.png");
  compose(slide, ctx, [
    ...header(ctx, slide, "Actual Memgraph evidence", "실제 DB에는 검수 후보, chunk, review note, memory가 graph로 연결되어 있다", "Memgraph Lab에서 같은 쿼리로 확인한 결과다. 발표용 mock이 아니라 현재 DB의 graph results 화면을 사용한다.", 9),
    rect(ctx, 64, 190, 610, 390, P.paper, { lineColor: "#E2D8D0", radius: 18 }),
    txt(ctx, "Memgraph Lab graph result", 96, 218, 300, 24, `font-size: 22px; font-weight: 800; color: ${P.ink}`),
    txt(ctx, "MATCH p=()-[]-() RETURN p", 410, 224, 210, 16, `font-size: 11px; color: ${P.muted}; alignment: right`),
    rect(ctx, 92, 258, 548, 284, "#FBFAF8", { lineColor: "#EFE7E1", radius: 12 }),
    txt(ctx, "graph image loading...", 284, 388, 180, 18, `font-size: 13px; color: ${P.muted}; alignment: center`),
    rect(ctx, 706, 190, 500, 390, "#FFFCF8", { lineColor: "#E2D8D0", radius: 18 }),
    txt(ctx, "Current graph facts", 738, 218, 250, 24, `font-size: 22px; font-weight: 800; color: ${P.ink}`),
    ...metric(ctx, "87", "nodes in current Memgraph", 744, 268, 136, P.purple),
    ...metric(ctx, "213", "edges in current Memgraph", 904, 268, 136, P.teal),
    ...metric(ctx, "42", "RelationshipCandidate nodes", 1064, 268, 136, P.amber),
    txt(ctx, "Node labels", 744, 374, 120, 18, `font-size: 12px; font-weight: 800; color: ${P.muted}`),
    ...pill(ctx, "Document 2", 744, 402, 110, P.blue, P.blueSoft),
    ...pill(ctx, "Chunk 35", 866, 402, 100, P.teal, P.tealSoft),
    ...pill(ctx, "Candidate 42", 978, 402, 124, P.amber, P.amberSoft),
    ...pill(ctx, "ReviewNote 5", 744, 442, 124, P.rose, P.roseSoft),
    ...pill(ctx, "Memory 1", 880, 442, 100, P.purple, P.purpleSoft),
    ...pill(ctx, "IngestJob 2", 992, 442, 112, P.green, P.greenSoft),
    txt(ctx, "Top edge types", 744, 500, 120, 18, `font-size: 12px; font-weight: 800; color: ${P.muted}`),
    txt(ctx, "CANDIDATE_LEFT / CANDIDATE_RIGHT / EVIDENCES_RELATIONSHIP_CANDIDATE / HAS_CHUNK / RELATED_TO", 744, 528, 386, 34, `font-size: 13px; color: ${P.ink}; leading: 1.15`),
    rect(ctx, 180, 604, 920, 42, "#FFF9F3", { lineColor: "#E2C8B0", radius: 14 }),
    txt(ctx, "핵심 증거: LLM output이 곧 edge가 아니라, Candidate와 ReviewNote를 거쳐 Memory/approved edge로 이어지는 graph 구조가 실제 DB에 존재한다.", 210, 616, 860, 18, `font-size: 14.5px; font-weight: 800; color: ${P.brown}; alignment: center`),
  ]);
  await ctx.addImage(slide, { path: graphPath, left: 100, top: 264, width: 532, height: 270, fit: "contain", alt: "Memgraph Lab graph cluster" });
  return slide;
}

function slide10(presentation, ctx) {
  const slide = presentation.slides.add();
  compose(slide, ctx, [
    ...header(ctx, slide, "Node / edge schema and construction pipeline", "DB schema는 document chunking, candidate review, memory feedback을 분리한다", "pipeline은 같은 graph DB에 쓰지만, candidate와 approved edge의 의미를 다르게 유지한다.", 10),
    rect(ctx, 60, 190, 560, 390, P.paper, { lineColor: "#E2D8D0", radius: 18 }),
    txt(ctx, "Clean node / edge structure", 92, 218, 300, 24, `font-size: 22px; font-weight: 800; color: ${P.ink}`),
    txt(ctx, "candidate는 검수용 artifact, approved edge는 별도 graph truth", 92, 250, 430, 18, `font-size: 12px; color: ${P.muted}`),
    rect(ctx, 100, 292, 154, 78, P.blueSoft, { lineColor: P.blue, radius: 12 }),
    txt(ctx, "Document", 118, 312, 118, 20, `font-size: 17px; font-weight: 800; color: ${P.ink}`),
    txt(ctx, "raw content\nmetadata\nDB UUID", 118, 338, 104, 30, `font-size: 10.5px; color: ${P.muted}; leading: 1.02`),
    rect(ctx, 364, 292, 164, 78, P.tealSoft, { lineColor: P.teal, radius: 12 }),
    txt(ctx, "Chunk", 382, 312, 118, 20, `font-size: 17px; font-weight: 800; color: ${P.ink}`),
    txt(ctx, "text + embedding\nname + description\nDB UUID", 382, 338, 128, 30, `font-size: 10.5px; color: ${P.muted}; leading: 1.02`),
    hline(ctx, 254, 332, 110, P.blue, 2),
    txt(ctx, "HAS_CHUNK", 266, 306, 86, 14, `font-size: 10px; font-weight: 800; color: ${P.blue}; alignment: center`),
    arrow(ctx, 296, 316, P.blue),
    rect(ctx, 198, 414, 244, 74, P.amberSoft, { lineColor: P.amber, radius: 12 }),
    txt(ctx, "RelationshipCandidate", 216, 432, 208, 18, `font-size: 16px; font-weight: 800; color: ${P.ink}; alignment: center`),
    txt(ctx, "left/right chunks · evidence · rationale · status", 218, 458, 204, 16, `font-size: 10.5px; color: ${P.muted}; alignment: center`),
    vline(ctx, 178, 370, 44, P.amber, 2),
    hline(ctx, 178, 414, 20, P.amber, 2),
    vline(ctx, 446, 370, 44, P.amber, 2),
    hline(ctx, 442, 414, 20, P.amber, 2),
    txt(ctx, "CANDIDATE_LEFT", 94, 386, 112, 14, `font-size: 9.5px; font-weight: 800; color: ${P.amber}; alignment: center`),
    txt(ctx, "CANDIDATE_RIGHT", 400, 386, 120, 14, `font-size: 9.5px; font-weight: 800; color: ${P.amber}; alignment: center`),
    rect(ctx, 94, 508, 150, 54, P.roseSoft, { lineColor: P.rose, radius: 12 }),
    txt(ctx, "ReviewNote", 110, 524, 118, 16, `font-size: 14px; font-weight: 800; color: ${P.ink}; alignment: center`),
    txt(ctx, "user feedback", 112, 544, 114, 12, `font-size: 9.8px; color: ${P.muted}; alignment: center`),
    hline(ctx, 244, 536, 72, P.rose, 2),
    txt(ctx, "HAS_REVIEW_NOTE", 226, 502, 118, 12, `font-size: 9px; font-weight: 800; color: ${P.rose}; alignment: center`),
    rect(ctx, 432, 508, 142, 54, P.purpleSoft, { lineColor: P.purple, radius: 12 }),
    txt(ctx, "Memory", 452, 524, 104, 16, `font-size: 14px; font-weight: 800; color: ${P.ink}; alignment: center`),
    txt(ctx, "next agent context", 448, 544, 112, 12, `font-size: 9.8px; color: ${P.muted}; alignment: center`),
    hline(ctx, 342, 536, 90, P.purple, 2),
    txt(ctx, "EVIDENCES_MEMORY", 330, 502, 128, 12, `font-size: 9px; font-weight: 800; color: ${P.purple}; alignment: center`),
    ...pill(ctx, "approved edge is graph truth", 390, 220, 190, P.green, P.greenSoft),
    rect(ctx, 660, 190, 560, 390, "#FFFCF8", { lineColor: "#E2D8D0", radius: 18 }),
    txt(ctx, "Construction pipeline", 692, 218, 260, 24, `font-size: 22px; font-weight: 800; color: ${P.ink}`),
    ...smallNode(ctx, "upload", 694, 286, 110, P.brown, P.brownSoft),
    arrow(ctx, 814, 298),
    ...smallNode(ctx, "register Document", 856, 286, 150, P.blue, P.blueSoft),
    arrow(ctx, 1016, 298),
    ...smallNode(ctx, "enqueue job", 1060, 286, 120, P.purple, P.purpleSoft),
    ...smallNode(ctx, "document_load", 694, 390, 130, P.brown, P.brownSoft),
    arrow(ctx, 834, 402),
    ...smallNode(ctx, "chunking_agent", 880, 390, 145, P.teal, P.tealSoft),
    arrow(ctx, 1034, 402),
    ...smallNode(ctx, "embedding", 1082, 390, 110, P.blue, P.blueSoft),
    ...smallNode(ctx, "graph_candidate", 812, 494, 150, P.purple, P.purpleSoft),
    arrow(ctx, 974, 506),
    ...smallNode(ctx, "pending review", 1024, 494, 130, P.amber, P.amberSoft),
    txt(ctx, "state: job_id + document_id + chunk_ids only", 694, 604, 490, 18, `font-size: 14px; font-weight: 800; color: ${P.brown}; alignment: center`),
  ]);
  return slide;
}

function slide11(presentation, ctx) {
  const slide = presentation.slides.add();
  compose(slide, ctx, [
    ...header(ctx, slide, "Agent harness and tool surface", "Graph candidate agent의 권한을 context/read/search/write로 제어", "agent가 DB를 마음대로 수정하지 않고 검수 대상 RelationshipCandidate만 만들도록 tool surface를 좁혔다.", 11),
    rect(ctx, 472, 290, 330, 112, P.dark, { lineColor: P.dark, radius: 20 }),
    txt(ctx, "graph_candidate_agent", 492, 320, 300, 28, `font-size: 22px; font-weight: 800; color: #FFFFFF; alignment: center`),
    txt(ctx, "given job_id · document_id · chunk_ids", 520, 356, 230, 18, `font-size: 12px; color: #D8D4E0; alignment: center`),
    ...node(ctx, "Injected context", "Memory document is injected automatically, not hidden behind optional tool usage.", 78, 210, 310, 104, P.brown, P.brownSoft),
    ...node(ctx, "Memgraph read tools", "schema, text, vector, traverse, read query primitives.", 78, 408, 310, 104, P.teal, P.tealSoft),
    ...node(ctx, "Firecrawl web search", "외부 근거가 필요할 때 보조 검색. graph evidence보다 우선하지 않음.", 892, 210, 310, 104, P.blue, P.blueSoft),
    ...node(ctx, "Candidate write only", "write_relationship_candidate_tool만 DB write surface로 제공.", 892, 408, 310, 104, P.amber, P.amberSoft),
    arrow(ctx, 404, 252),
    arrow(ctx, 404, 452, P.teal),
    arrow(ctx, 832, 252, P.blue),
    arrow(ctx, 832, 452, P.amber),
    rect(ctx, 244, 574, 790, 54, "#FFF9F3", { lineColor: "#E2C8B0", radius: 14 }),
    txt(ctx, "원본 document 전체를 LLM context에 싣지 않고 chunk/document id 기반 query로 필요한 부분만 읽게 한다.", 274, 592, 730, 20, `font-size: 16px; font-weight: 700; color: ${P.brown}; alignment: center`),
  ]);
  return slide;
}

function slide12(presentation, ctx) {
  const slide = presentation.slides.add();
  compose(slide, ctx, [
    ...header(ctx, slide, "Review queue", "Candidate first, edge later", "LLM이 만든 관계는 바로 graph edge가 아니라 사람이 승인하는 RelationshipCandidate가 된다.", 12),
    ...node(ctx, "LLM Agent", "관계 후보 제안", 78, 302, 160, 82, P.purple, P.purpleSoft),
    arrow(ctx, 256, 326, P.purple),
    ...node(ctx, "RelationshipCandidate", "pending_review\nsource/target/rationale/evidence", 316, 280, 230, 126, P.amber, P.amberSoft),
    arrow(ctx, 566, 326, P.amber),
    rect(ctx, 626, 220, 260, 246, P.paper, { lineColor: "#DEC8BA", radius: 18 }),
    txt(ctx, "Human Review", 660, 252, 190, 28, `font-size: 24px; font-weight: 800; color: ${P.brown}`),
    txt(ctx, "source chunk, target chunk, AI rationale, evidence, confidence를 보고 approve/deny를 staging한다.", 660, 304, 186, 70, `font-size: 15px; color: ${P.ink}; leading: 1.15`),
    ...pill(ctx, "Approve", 660, 396, 100, P.green, P.greenSoft),
    ...pill(ctx, "Deny", 774, 396, 80, P.rose, P.roseSoft),
    arrow(ctx, 908, 326),
    ...node(ctx, "Atomic Commit", "approve된 후보만 실제 edge로 materialize", 966, 268, 210, 92, P.green, P.greenSoft),
    ...node(ctx, "Rejected Artifact", "deny된 후보도 판단 이력으로 보존", 966, 390, 210, 92, P.rose, P.roseSoft),
    rect(ctx, 190, 584, 900, 42, "#FFF9F3", { lineColor: "#E2C8B0", radius: 14 }),
    txt(ctx, "검수 가능한 자동화: LLM output은 제안이고 DB graph truth는 review 이후에만 바뀐다.", 220, 596, 840, 18, `font-size: 16px; font-weight: 800; color: ${P.brown}; alignment: center`),
  ]);
  return slide;
}

function slide13(presentation, ctx) {
  const slide = presentation.slides.add();
  compose(slide, ctx, [
    ...header(ctx, slide, "Memory feedback and observability", "Reviewer note는 다음 agent 판단 기준이 되고, agent event는 Redis Stream으로 보인다", "운영하면서 개선 가능하게 만드는 memory layer와 debugging visibility를 한 장에 묶었다.", 13),
    ...node(ctx, "RelationshipCandidate", "approve/deny 대상", 72, 238, 210, 82, P.amber, P.amberSoft),
    arrow(ctx, 300, 260),
    ...node(ctx, "ReviewNote", "사용자 판단 이유", 356, 238, 190, 82, P.brown, P.brownSoft),
    arrow(ctx, 564, 260),
    ...node(ctx, "memory_update_agent", "job note와 candidate context를 보고 Memory 재작성", 622, 238, 240, 82, P.purple, P.purpleSoft),
    arrow(ctx, 880, 260),
    ...node(ctx, "Memory", "다음 candidate agent context에 자동 주입", 936, 238, 230, 82, P.teal, P.tealSoft),
    hline(ctx, 184, 374, 914, P.teal, 3),
    txt(ctx, "모델 파라미터 학습이 아니라 system memory document 업데이트", 356, 392, 560, 18, `font-size: 15px; font-weight: 800; color: ${P.teal}; alignment: center`),
    ...node(ctx, "Worker runner", "task lifecycle event", 110, 498, 180, 74, P.brown, P.brownSoft),
    ...node(ctx, "Agent runtime", "model token · tool call · transcript", 110, 594, 180, 54, P.purple, P.purpleSoft),
    arrow(ctx, 316, 530),
    rect(ctx, 376, 504, 210, 104, P.dark, { lineColor: P.dark, radius: 18 }),
    txt(ctx, "Redis Streams", 414, 534, 140, 24, `font-size: 22px; font-weight: 800; color: #FFFFFF; alignment: center`),
    txt(ctx, "recent observability events", 410, 568, 145, 18, `font-size: 11px; color: #D7D2DE; alignment: center`),
    arrow(ctx, 606, 532),
    ...node(ctx, "SSE / Polling", "event stream + status refresh", 666, 516, 190, 76, P.blue, P.blueSoft),
    arrow(ctx, 876, 532),
    ...node(ctx, "Diagnostics Studio", "agent event terminal", 936, 516, 210, 76, P.green, P.greenSoft),
  ]);
  return slide;
}

async function slide14(presentation, ctx) {
  const slide = presentation.slides.add();
  const chartPath = path.join(process.cwd(), "presentation/test-data/no-tool-benchmark/charts/cost_vs_latency_scatter.png");
  const qs = [
    ["RAG-Q-008", "과도한 일반화", "기초연금 무조건 지급 단정 방지"],
    ["RAG-Q-009", "법률 단정", "나이 제한 전부 불법 단정 방지"],
    ["RAG-Q-012", "문서 범위", "법령과 시설 데이터 혼동 방지"],
    ["RAG-Q-334", "가짜 연락처", "없는 전화번호 생성 금지"],
    ["RAG-Q-351", "통계 추론", "집계 감소를 폐쇄로 단정 금지"],
  ];
  compose(slide, ctx, [
    ...header(ctx, slide, "Validation plan and closing", "360개 테스트 셋과 no-tool benchmark는 확보, tool-attached 검증은 다음 단계", "시스템 프롬프트와 edge case 질문을 hallucination/source grounding 검증 근거로 연결한다.", 14),
    rect(ctx, 70, 184, 520, 370, P.paper, { lineColor: "#E2D8D0", radius: 18 }),
    txt(ctx, "Representative edge cases", 102, 214, 320, 24, `font-size: 22px; font-weight: 800; color: ${P.ink}`),
    ...qs.map((q, i) => {
      const yy = 264 + i * 52;
      return [
        txt(ctx, q[0], 104, yy, 92, 18, `font-size: 12px; font-weight: 800; color: ${P.purple}`),
        txt(ctx, q[1], 204, yy, 100, 18, `font-size: 12px; font-weight: 800; color: ${P.brown}`),
        txt(ctx, q[2], 318, yy, 220, 20, `font-size: 12px; color: ${P.muted}`),
        hline(ctx, 102, yy + 32, 430, "#EEE7E1", 1),
      ];
    }),
    rect(ctx, 650, 184, 520, 320, P.paper, { lineColor: "#E2D8D0", radius: 18 }),
    txt(ctx, "Actual benchmark chart", 680, 212, 240, 20, `font-size: 18px; font-weight: 800; color: ${P.ink}`),
    txt(ctx, "source: cost_vs_latency_scatter.png", 934, 214, 190, 16, `font-size: 10.5px; color: ${P.muted}; alignment: right`),
    rect(ctx, 676, 244, 468, 232, "#FFFFFF", { lineColor: "#EFE7E1", radius: 10 }),
    txt(ctx, "image loading...", 840, 350, 140, 18, `font-size: 13px; color: ${P.muted}; alignment: center`),
    rect(ctx, 650, 526, 520, 66, "#FFF9F3", { lineColor: "#E2C8B0", radius: 16 }),
    txt(ctx, "남은 검증", 680, 546, 100, 18, `font-size: 13px; font-weight: 800; color: ${P.brown}`),
    txt(ctx, "MCP tool을 붙인 동일 360개 질문 재실행 → retrieval quality, citation grounding, tool error/latency/cost 비교", 780, 540, 350, 30, `font-size: 13px; color: ${P.muted}; leading: 1.15`),
    txt(ctx, "근거: backend system prompt, rag_agent_question_test_cases_360.md, no_tool_provider_summary.csv", 86, 626, 980, 18, `font-size: 11px; color: ${P.muted}`),
  ]);
  await ctx.addImage(slide, { path: chartPath, left: 680, top: 248, width: 460, height: 224, fit: "contain", alt: "cost versus latency scatter chart" });
  return slide;
}

const slides = [
  slide01,
  slide02,
  slide03,
  slide04,
  slide05,
  slide06,
  slide07,
  slide08,
  slide09,
  slide10,
  slide11,
  slide12,
  slide13,
  slide14,
];

export async function addDeckSlide(presentation, ctx, index) {
  return slides[index - 1](presentation, ctx);
}
