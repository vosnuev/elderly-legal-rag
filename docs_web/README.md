# SKN28-3rd-1Team Docs Web

프로젝트 소개, 기술 스택, 프론트엔드/백엔드/RAG 작업 방향을 한 화면에서 확인하는 문서 웹입니다.

## Stack

- Vite
- React
- TypeScript
- Tailwind CSS
- shadcn/ui

## Local Run

```bash
npm install
npm run dev
```

## Build

```bash
npm run build
npm run preview
```

GitHub Pages 배포를 위해 `vite.config.ts`의 `base`는 `/SKN28-3rd-1Team/`로 설정되어 있습니다.

## Deploy

`main` 브랜치에 병합되면 GitHub Actions가 `docs_web/dist`를 GitHub Pages artifact로 업로드하고 배포합니다. 수동 실행이 필요한 경우에도 `main` ref에서 실행해야 GitHub Pages 환경 보호 규칙을 통과합니다.

- 예상 Pages URL: <https://sknetworks-family-aicamp.github.io/SKN28-3rd-1Team/>
- 실제 배포 URL: Actions의 `github-pages` environment URL과 workflow summary의 `Docs Web URL`에서 확인합니다.
