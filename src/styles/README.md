# Key Therapy — CSS 모듈 구조

> 14k 줄 단일 HTML의 inline `<style>`을 점진 분리·정식화한 CSS 모듈.
> S5 작업 산출물. 실제 적용은 S4 Vite 셋업 완료 후 진행.

## 디렉토리 구조

```
src/styles/
├── index.css              ← 진입점 (Vite import 대상)
├── tokens.css             ← Foundation·Semantic·Theme 토큰
├── base.css               ← Reset·typography·접근성 기본
├── components/
│   ├── hero.css           ← .kt-hero (BEM-lite 시범)
│   ├── controls.css       ← .kt-controls·.kt-mode-buttons·.kt-selection
│   └── ...                (다음 단계: typing-area, ambience, freestyle, game, asmr, modal, stats, footer)
├── responsive/
│   └── mobile.css         ← 통합 모바일 (M1-M11 정리, breakpoint 4개)
└── COLOR_CONTRAST_AUDIT.md ← WCAG AA 색상 대비 검증 보고서
```

## 적용 흐름 (사용자 환경에서)

S4 Vite 셋업 완료 후:

### 1. CSS import 추가
`index.html`의 `<head>`에:
```html
<link rel="stylesheet" href="/src/styles/index.css">
```

### 2. inline `<style>` 점진 제거
`index.html`의 inline `<style>` 안에서 다음 영역을 한 블록씩 잘라내고, `src/styles/components/[name].css`로 옮겨, 클래스명을 BEM-lite로 교체:

| 단계 | 영역 | inline 위치 | 새 파일 |
|---|---|---|---|
| ✅ 1 | `:root` 변수 | line 3217~ | `tokens.css` |
| ✅ 2 | html/body reset | line 3266~ | `base.css` |
| ✅ 3 | `.hero-section` | line 3337~ | `components/hero.css` |
| ✅ 4 | `.practice-mode-controls` 등 | line 3447~ | `components/controls.css` |
| ⏳ 5 | `.typing-area-container` | line 3675~ | `components/typing-area.css` |
| ⏳ 6 | `#ambience-layer` 등 | line 4796~ | `components/ambience.css` |
| ⏳ 7 | `#freestyle-area-container` | line 2258~ | `components/freestyle.css` |
| ⏳ 8 | `#game-canvas` 등 | line 1454~ | `components/game.css` |
| ⏳ 9 | `#asmr-overlay` | line 2552~ | `components/asmr.css` |
| ⏳ 10 | `#helpModal` `#result-card-modal` | line 6328~, line 2890~ | `components/modal.css` |
| ⏳ 11 | `#stats` | line 3614~ | `components/stats.css` |
| ⏳ 12 | `.footer` | line ~ | `components/footer.css` |
| ✅ 13 | mobile responsive [M1-M11] | line 6090~ | `responsive/mobile.css` |

## 핵심 원칙

1. **selector 깊이 ≤ 2** — `.typing-area-container .typing-line` 같은 깊은 선택자 금지. 단일 클래스 `.kt-typing-line--current`로 변환
2. **`!important` 사용 0** — `@layer` 통제로 cascade 자동 정리
3. **테마는 부모 클래스에서 변수만 재정의** — `.light-theme .button` 같은 카운터-셀렉터 금지
4. **컴포넌트 CSS는 `@layer components`** — utilities·responsive보다 낮은 우선순위
5. **모든 색·간격·radius·shadow는 토큰 참조** — 하드코딩 0

## 토큰 사용 예시

```css
/* ❌ 안 좋음 — 하드코딩 */
.kt-button {
  color: #f2e7d6;
  padding: 8px 16px;
  border-radius: 12px;
  background: rgba(212, 175, 122, 0.18);
}

/* ✅ 좋음 — 토큰 참조 */
.kt-button {
  color: var(--kt-text-primary);
  padding: var(--kt-space-2) var(--kt-space-4);
  border-radius: var(--kt-radius-md);
  background: rgba(var(--kt-color-amber-rgb), 0.18);
}
```

## 검증 (사용자 환경)

```bash
# 1. 새 CSS 모듈만 적용했을 때 시각적 동일성 확인
npm run dev
# → 브라우저에서 hero / controls 영역이 inline 시절과 동일한지 비교

# 2. !important 카운트 체크
grep -c "!important" src/styles/**/*.css
# 목표: < 50 (현재 inline은 893)

# 3. WCAG 대비 검증
npx @axe-core/cli http://localhost:5173 --tags wcag2aa
# 목표: 0 violation
```

## 향후 작업 (S6, S7)

- **S6 (JS 모듈 분리)**: 각 컴포넌트 CSS와 짝을 이루는 JS 모듈 생성 (예: `hero.js`, `controls.js`)
- **S7 (반응형·!important 정리)**: 인라인 CSS의 잔존 `!important` 점진 제거. breakpoint 4개로 통일

---

*마지막 갱신: 2026-04-27*
*S5 산출물 — 5개 핵심 CSS 모듈 + 색상 대비 audit + 진입점 + README*
