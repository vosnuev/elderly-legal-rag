import {
  BookOpenText,
  Braces,
  Database,
  FileText,
  GitBranch,
  GitPullRequest,
  LayoutDashboard,
  Menu,
  MessageSquareText,
  Network,
  PanelsTopLeft,
  Server,
} from 'lucide-react'
import type { ReactNode } from 'react'

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet'

const teamMembers = [
  { name: '이원빈', role: '팀장', responsibility: '전체 컨펌 및 총괄 관리' },
  { name: '김지효', role: 'RAG 담당', responsibility: '임베딩, 문서 전처리' },
  { name: '송윤경', role: '프론트엔드', responsibility: '엔드포인트 연결, UI 구현' },
  { name: '전하영', role: '백엔드', responsibility: 'MCP 툴 연동, API/엔드포인트 구현' },
  { name: '양도영', role: '플로우 정리', responsibility: 'PPT 제작, 전체 내용 정리' },
]

const navGroups = [
  {
    value: 'project',
    label: 'Project',
    icon: BookOpenText,
    links: [
      { href: '#overview', label: '개요' },
      { href: '#team', label: '팀원 및 역할' },
      { href: '#users', label: '사용자 문제' },
    ],
  },
  {
    value: 'frontend',
    label: 'Frontend',
    icon: PanelsTopLeft,
    links: [
      { href: '#frontend', label: '사용자 화면' },
      { href: '#frontend-plan', label: '구현 방향' },
    ],
  },
  {
    value: 'backend',
    label: 'Backend',
    icon: Server,
    links: [
      { href: '#backend', label: 'API 서비스' },
      { href: '#backend-plan', label: '구현 방향' },
    ],
  },
  {
    value: 'rag',
    label: 'RAG',
    icon: Network,
    links: [
      { href: '#rag', label: '검색 파이프라인' },
      { href: '#rag-plan', label: '문서 처리' },
    ],
  },
  {
    value: 'collaboration',
    label: 'Collaboration',
    icon: GitBranch,
    links: [
      { href: '#collaboration', label: '협업 도구' },
      { href: '#workflow', label: '작업 규칙' },
    ],
  },
]

const techRows = [
  {
    area: 'Frontend',
    icon: PanelsTopLeft,
    stack: 'React, TypeScript, Tailwind CSS, shadcn/ui',
    plan: '질의 입력, 답변, 출처, 예외 상태를 사용자가 빠르게 확인할 수 있는 화면을 담당합니다.',
  },
  {
    area: 'Backend',
    icon: Server,
    stack: 'Python, FastAPI, Pydantic, LangChain, LangGraph',
    plan: 'API 엔드포인트, 설정 로딩, RAG 호출, MCP 도구 연동을 단일 서비스 경계로 관리합니다.',
  },
  {
    area: 'RAG',
    icon: Network,
    stack: 'Microsoft GraphRAG, Vector DB 후보, 문서 메타데이터',
    plan: '법령과 복지 문서를 조항 단위로 검색하고, 답변 근거를 함께 제공하는 파이프라인을 구성합니다.',
  },
  {
    area: 'Prototype',
    icon: LayoutDashboard,
    stack: 'Streamlit, uv, Python',
    plan: '초기 실험과 데모를 빠르게 확인하는 프로토타입 실행 환경으로 사용합니다.',
  },
]

const collaborationTools = [
  { name: 'GitHub', detail: '브랜치, PR, 코드 리뷰, GitHub Pages 배포' },
  { name: 'Linear', detail: '일정, 이슈, 작업 상태 추적' },
  { name: 'Notion', detail: '자료 링크, 회의 기록, 정책 문서 정리' },
  { name: 'Discord', detail: '실시간 커뮤니케이션과 작업 공유' },
]

function SidebarContent() {
  return (
    <div className="flex h-full flex-col bg-white">
      <div className="border-b border-slate-200 px-5 py-5">
        <a href="#overview" className="flex items-center gap-2 text-sm font-semibold text-slate-950">
          <span className="flex size-8 items-center justify-center overflow-hidden rounded-md border border-blue-100 bg-blue-50">
            <img src="/old_robot.png" alt="" aria-hidden="true" className="size-6 object-contain" />
          </span>
          SKN28-3rd-1Team
        </a>
        <p className="mt-2 text-xs leading-5 text-slate-600">
          장애인·취약계층 복지/법률 RAG Agent 문서
        </p>
      </div>

      <ScrollArea className="min-h-0 flex-1 px-3 py-4">
        <Accordion
          type="multiple"
          defaultValue={['project', 'frontend', 'backend', 'rag']}
          className="gap-1"
        >
          {navGroups.map((group) => {
            const Icon = group.icon

            return (
              <AccordionItem
                key={group.value}
                value={group.value}
                className="border-0"
              >
                <AccordionTrigger className="rounded-md px-2 py-2 text-[13px] font-semibold text-slate-800 no-underline hover:bg-slate-100 hover:no-underline">
                  <span className="flex items-center gap-2">
                    <Icon className="size-4 text-slate-500" aria-hidden="true" />
                    {group.label}
                  </span>
                </AccordionTrigger>
                <AccordionContent className="pb-1 pl-8">
                  <nav className="flex flex-col gap-1">
                    {group.links.map((link) => (
                      <a
                        key={link.href}
                        href={link.href}
                        className="rounded-md px-2 py-1.5 text-[13px] leading-5 text-slate-600 hover:bg-blue-50 hover:text-blue-800"
                      >
                        {link.label}
                      </a>
                    ))}
                  </nav>
                </AccordionContent>
              </AccordionItem>
            )
          })}
        </Accordion>
      </ScrollArea>
    </div>
  )
}

function MobileNav() {
  return (
    <Sheet>
      <SheetTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="lg:hidden"
          aria-label="문서 목차 열기"
        >
          <Menu className="size-5" aria-hidden="true" />
        </Button>
      </SheetTrigger>
      <SheetContent side="left" className="w-[300px] max-w-[85vw] p-0">
        <SheetHeader className="sr-only">
          <SheetTitle>문서 목차</SheetTitle>
          <SheetDescription>프로젝트 문서 섹션으로 이동합니다.</SheetDescription>
        </SheetHeader>
        <SidebarContent />
      </SheetContent>
    </Sheet>
  )
}

function SectionHeading({
  id,
  eyebrow,
  title,
  children,
}: {
  id: string
  eyebrow: string
  title: string
  children: ReactNode
}) {
  return (
    <section id={id} className="scroll-mt-24">
      <p className="text-xs font-semibold uppercase tracking-[0.14em] text-blue-700">
        {eyebrow}
      </p>
      <h2 className="mt-2 text-2xl font-semibold text-slate-950">{title}</h2>
      <div className="mt-4 text-[15px] leading-7 text-slate-700">{children}</div>
    </section>
  )
}

function App() {
  return (
    <div className="min-h-screen bg-[#f8fafc] text-slate-900">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-[286px] border-r border-slate-200 bg-white lg:block">
        <SidebarContent />
      </aside>

      <div className="lg:pl-[286px]">
        <header className="sticky top-0 z-20 flex h-14 items-center justify-between border-b border-slate-200 bg-white/95 px-4 backdrop-blur lg:px-8">
          <div className="flex min-w-0 items-center gap-2">
            <MobileNav />
            <img src="/old_robot.png" alt="" aria-hidden="true" className="size-7 object-contain" />
            <span className="truncate text-sm font-semibold text-slate-950">
              복지/법률 RAG Agent Docs
            </span>
          </div>
          <div className="flex items-center gap-1">
            <Button asChild variant="ghost" size="sm">
              <a
                href="https://github.com/SKNETWORKS-FAMILY-AICAMP/SKN28-3rd-1Team"
                target="_blank"
                rel="noreferrer"
              >
                <GitPullRequest className="size-4" aria-hidden="true" />
                GitHub
              </a>
            </Button>
            <Button asChild variant="ghost" size="sm" className="hidden sm:inline-flex">
              <a
                href="https://linear.app/skn28-3rd/team/SKN/all"
                target="_blank"
                rel="noreferrer"
              >
                <GitBranch className="size-4" aria-hidden="true" />
                Linear
              </a>
            </Button>
          </div>
        </header>

        <main className="mx-auto max-w-[980px] px-5 py-8 sm:px-8 lg:py-12">
          <section id="overview" className="scroll-mt-24">
            <div className="mb-5 flex flex-wrap items-center gap-2 text-xs font-medium text-slate-600">
              <span className="rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-blue-800">
                RAG Agent
              </span>
              <span className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-emerald-800">
                공공문서 기반
              </span>
              <span className="rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-amber-800">
                출처 제공
              </span>
            </div>
            <h1 className="max-w-[760px] text-3xl font-semibold leading-tight text-slate-950 sm:text-4xl">
              장애인·취약계층 복지/법률 RAG Agent
            </h1>
            <p className="mt-5 max-w-[780px] text-base leading-8 text-slate-700">
              여러 기관에 흩어진 복지, 노동, 고용 관련 문서를 검색해 사용자가 받을 수 있는
              혜택과 대응 절차를 자연어로 확인할 수 있게 만드는 팀 프로젝트입니다. 답변은
              최신 공식 문서와 법령 근거를 함께 제공하는 방향으로 설계합니다.
            </p>
          </section>

          <Separator className="my-10 bg-slate-200" />

          <SectionHeading id="team" eyebrow="Team" title="팀원 및 역할">
            <div className="overflow-hidden rounded-md border border-slate-200 bg-white">
              <table className="w-full border-collapse text-left text-sm">
                <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                  <tr>
                    <th className="px-4 py-3 font-semibold">이름</th>
                    <th className="px-4 py-3 font-semibold">역할</th>
                    <th className="px-4 py-3 font-semibold">담당 범위</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {teamMembers.map((member) => (
                    <tr key={member.name}>
                      <td className="px-4 py-3 font-medium text-slate-950">{member.name}</td>
                      <td className="px-4 py-3 text-slate-700">{member.role}</td>
                      <td className="px-4 py-3 text-slate-600">{member.responsibility}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </SectionHeading>

          <Separator className="my-10 bg-slate-200" />

          <SectionHeading id="users" eyebrow="Problem" title="사용자 문제와 해결 방향">
            <div className="grid gap-4 md:grid-cols-3">
              {[
                ['정보 접근', '기관별로 흩어진 복지·고용 정보를 한 번의 질의로 확인합니다.'],
                ['법률 이해', '전문 용어와 복잡한 조건을 사용자가 이해 가능한 설명으로 바꿉니다.'],
                ['신뢰성', '최신 문서 기반 검색과 출처 제공으로 환각 위험을 줄입니다.'],
              ].map(([title, detail]) => (
                <div key={title} className="rounded-md border border-slate-200 bg-white p-4">
                  <h3 className="text-sm font-semibold text-slate-950">{title}</h3>
                  <p className="mt-2 text-sm leading-6 text-slate-600">{detail}</p>
                </div>
              ))}
            </div>
          </SectionHeading>

          <Separator className="my-10 bg-slate-200" />

          <SectionHeading id="frontend" eyebrow="Frontend" title="사용자 화면">
            <p>
              프론트엔드는 자연어 질문 입력, 답변 확인, 근거 문서 탐색, 오류 상태 안내를
              담당합니다. 접근성과 반복 사용성을 우선으로 두고, 답변과 출처를 한 화면에서
              비교할 수 있는 구성을 목표로 합니다.
            </p>
            <div id="frontend-plan" className="mt-5 rounded-md border border-slate-200 bg-white p-5">
              <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-950">
                <Braces className="size-4 text-blue-700" aria-hidden="true" />
                구현 방향
              </h3>
              <ul className="mt-3 space-y-2 text-sm leading-6 text-slate-600">
                <li>React와 TypeScript 기반의 화면 컴포넌트로 질의 흐름을 구성합니다.</li>
                <li>Tailwind CSS와 shadcn/ui를 사용해 일관된 라이트 모드 UI를 유지합니다.</li>
                <li>출처 문서, 관련 조항, 답변 생성 상태를 명확히 분리해서 보여줍니다.</li>
              </ul>
            </div>
          </SectionHeading>

          <Separator className="my-10 bg-slate-200" />

          <SectionHeading id="backend" eyebrow="Backend" title="API 서비스">
            <p>
              백엔드는 FastAPI를 중심으로 요청 검증, RAG 파이프라인 호출, 설정 관리,
              외부 도구 연동을 담당합니다. 서비스별 환경 변수는 Pydantic Settings로
              로딩해 설정 진입점을 단일화합니다.
            </p>
            <div id="backend-plan" className="mt-5 grid gap-3 sm:grid-cols-2">
              {[
                ['Entry Point', 'src/app.py를 API 애플리케이션 진입점으로 사용합니다.'],
                ['Settings', 'src/settings.py를 설정의 싱글 소스 오브 트루스로 둡니다.'],
                ['Contracts', '요청/응답 스키마는 Pydantic 모델로 명확히 관리합니다.'],
                ['Workflow', 'LangChain과 LangGraph로 RAG 호출 흐름을 조립합니다.'],
              ].map(([title, detail]) => (
                <div key={title} className="rounded-md border border-slate-200 bg-white p-4">
                  <h3 className="text-sm font-semibold text-slate-950">{title}</h3>
                  <p className="mt-2 text-sm leading-6 text-slate-600">{detail}</p>
                </div>
              ))}
            </div>
          </SectionHeading>

          <Separator className="my-10 bg-slate-200" />

          <SectionHeading id="rag" eyebrow="RAG" title="검색 파이프라인">
            <p>
              RAG 영역은 법령, 복지 지침, 고용 관련 PDF를 조항 단위로 정리하고 검색 품질을
              높이는 데 집중합니다. Microsoft GraphRAG를 검토 대상으로 두고, 문서 관계와
              출처 메타데이터를 함께 관리합니다.
            </p>
            <div id="rag-plan" className="mt-5 overflow-hidden rounded-md border border-slate-200 bg-white">
              <div className="grid border-b border-slate-200 bg-slate-50 px-4 py-3 text-xs font-semibold uppercase text-slate-500 sm:grid-cols-[160px_1fr]">
                <span>단계</span>
                <span>처리 내용</span>
              </div>
              {[
                ['Ingestion', 'PDF와 공공기관 문서를 수집하고 원본 출처를 기록합니다.'],
                ['Chunking', '법령 조항과 문서 섹션 단위로 청크를 나눕니다.'],
                ['Metadata', '문서명, 조항, 기관, 카테고리, 개정일을 함께 저장합니다.'],
                ['Retrieval', '사용자 질문과 관련 있는 근거 문서를 검색해 답변 생성에 전달합니다.'],
              ].map(([step, detail]) => (
                <div
                  key={step}
                  className="grid gap-1 border-b border-slate-100 px-4 py-3 text-sm last:border-b-0 sm:grid-cols-[160px_1fr]"
                >
                  <span className="font-medium text-slate-950">{step}</span>
                  <span className="text-slate-600">{detail}</span>
                </div>
              ))}
            </div>
          </SectionHeading>

          <Separator className="my-10 bg-slate-200" />

          <SectionHeading id="collaboration" eyebrow="Stack" title="기술과 협업 도구">
            <div className="grid gap-4">
              {techRows.map((row) => {
                const Icon = row.icon

                return (
                  <div
                    key={row.area}
                    className="grid gap-3 rounded-md border border-slate-200 bg-white p-4 sm:grid-cols-[170px_1fr]"
                  >
                    <div className="flex items-center gap-2 font-semibold text-slate-950">
                      <Icon className="size-4 text-blue-700" aria-hidden="true" />
                      {row.area}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-slate-800">{row.stack}</p>
                      <p className="mt-1 text-sm leading-6 text-slate-600">{row.plan}</p>
                    </div>
                  </div>
                )
              })}
            </div>

            <div id="workflow" className="mt-6 grid gap-4 md:grid-cols-2">
              <div className="rounded-md border border-slate-200 bg-white p-5">
                <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-950">
                  <MessageSquareText className="size-4 text-emerald-700" aria-hidden="true" />
                  협업 채널
                </h3>
                <div className="mt-4 space-y-3">
                  {collaborationTools.map((tool) => (
                    <div key={tool.name} className="grid grid-cols-[88px_1fr] gap-3 text-sm">
                      <span className="font-medium text-slate-950">{tool.name}</span>
                      <span className="leading-6 text-slate-600">{tool.detail}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-md border border-slate-200 bg-white p-5">
                <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-950">
                  <FileText className="size-4 text-amber-700" aria-hidden="true" />
                  작업 규칙
                </h3>
                <ul className="mt-4 space-y-2 text-sm leading-6 text-slate-600">
                  <li>main 브랜치에 직접 커밋하지 않고 PR 단위로 리뷰합니다.</li>
                  <li>의존성, 문서, 기능 변경은 가능한 한 작은 브랜치로 분리합니다.</li>
                  <li>커밋은 작업 의미가 분리되는 원자적 단위로 작성합니다.</li>
                  <li>문제 추적과 일정 공유는 Linear와 GitHub Issue를 함께 사용합니다.</li>
                </ul>
              </div>
            </div>
          </SectionHeading>

          <Separator className="my-10 bg-slate-200" />

          <section className="grid gap-4 rounded-md border border-slate-200 bg-white p-5 sm:grid-cols-[48px_1fr]">
            <div className="flex size-10 items-center justify-center rounded-md bg-blue-50 text-blue-700">
              <Database className="size-5" aria-hidden="true" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-slate-950">문서 데이터 후보</h2>
              <p className="mt-2 text-sm leading-7 text-slate-600">
                국가법령정보센터, 복지로, 한국장애인고용공단, 고용노동부 자료를 우선 검토하고
                문서별 출처와 개정일을 메타데이터로 남깁니다.
              </p>
            </div>
          </section>
        </main>
      </div>
    </div>
  )
}

export default App
