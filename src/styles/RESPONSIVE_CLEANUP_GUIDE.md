# Key Therapy — 반응형 & !important 정리 가이드 (S7)

> 인라인 CSS의 9개 혼재 breakpoint를 표준 4개로, !important 904회를 < 50회로 점진 축소하는 작업 가이드.
> 본 작업은 사용자 환경에서 신중히 진행해야 함 (시각 회귀 위험).

---

## 1. Breakpoint 분포 현황

| breakpoint | 사용 횟수 | 분류 | 통합 권장 |
|---|---|---|---|
| `1024px` | 1 | 표준 (desktop-tablet) | 그대로 |
| `920px` | 1 | 비표준 | → `1024px` |
| `860px` | 1 | 비표준 | → `768px` |
| `768px` | 16 | 표준 (tablet-mobile) | 그대로 |
| `720px` | 2 | 비표준 | → `768px` |
| `640px` | 3 | 비표준 | → `768px` |
| `480px` | 5 | 표준 (phone) | 그대로 |
| `380px` | 4 | 거의 표준 (narrow phone) | 그대로 (Galaxy Fold 등) |
| `360px` | 2 | 표준 (very narrow) | 그대로 |

**목표 4개 표준**: `1024 / 768 / 480 / 360`. 비표준 7곳을 표준으로 흡수.

## 2. 안전한 통합 절차

### 2-1. 사전 준비
1. 현재 사이트의 시각 회귀 비교용 스크린샷 (320·480·768·1024·1440 5개 viewport)
2. Vite 셋업 완료 (npm run dev로 즉시 검증 가능)
3. git 새 브랜치: `chore/cleanup-breakpoints`

### 2-2. 단계별 통합 (가장 안전한 순서)

**Step 1 — 720px → 768px (영향 작음)**

```bash
grep -n "max-width: 720px\|max-width:720px" index.html
# 위 출력 라인을 768px로 변경
```

각 변경 후:
- 브라우저에서 720px ~ 768px 범위 viewport 시각 점검
- 게임/단문/ASMR/글쓰기 모드 모두 확인

**Step 2 — 640px → 768px (영향 작음)**
**Step 3 — 920px → 1024px (영향 작음)**
**Step 4 — 860px → 768px (영향 클 수 있음, 신중)**

각 step마다 git commit 권장 — 회귀 시 즉시 롤백.

### 2-3. 새 컴포넌트 CSS는 표준 4개만

`src/styles/components/*.css` (S5·S7 산출물)는 이미 표준 4개만 사용. 신규 작성 시에도 이 룰 유지.

```css
/* ✅ 좋음 */
@media (max-width: 768px) { ... }
@media (max-width: 480px) { ... }

/* ❌ 안 좋음 */
@media (max-width: 720px) { ... }
@media (max-width: 860px) { ... }
```

---

## 3. !important 정리 전략

### 3-1. 현황 (904회 사용)

| 카테고리 | 횟수 | 정리 우선도 |
|---|---|---|
| `font-*` | 126 | 낮음 (정렬 위해 필요한 곳 많음) |
| `border-*` | 106 | 중 |
| `color` | 96 | 중 |
| `padding` | 95 | 높음 (대부분 specificity로 충분) |
| `background` | 86 | 중 |
| 기타 (margin/transform/opacity 등) | 395 | 낮음 |

### 3-2. 점진 정리 패턴

**Pattern A — `@layer` 도입 (가장 큰 효과)**

```css
/* 인라인 CSS 시작부 */
@layer reset, base, tokens, components, themes, utilities, responsive;

/* 모든 룰을 @layer 안으로 */
@layer base {
  body { background: var(--kt-surface-deep); /* !important 제거 */ }
}
@layer themes {
  .light-theme { --kt-color-bg-deep: #ece4d3; }
}
```

`@layer` 순서로 cascade가 자동 정렬되므로 `!important` 90% 이상 제거 가능.

**Pattern B — Selector 단순화 (selector 깊이 ≤ 2)**

```css
/* ❌ 깊은 셀렉터 + !important */
.typing-area-container .typing-line.current-to-type {
  font-size: 1.2rem !important;
}

/* ✅ BEM-lite 단일 클래스 — !important 불필요 */
.kt-typing__line--current {
  font-size: 1.2rem;
}
```

**Pattern C — 카운터 셀렉터 제거**

```css
/* ❌ */
.light-theme .button { background: #fff; }
.dark-theme .button { background: #000; }

/* ✅ 변수만 재정의 */
.button { background: var(--kt-action-bg); }
.light-theme { --kt-action-bg: #fff; }
.dark-theme { --kt-action-bg: #000; }
```

### 3-3. 검증

```bash
# 정리 전후 카운트 비교
grep -c "!important" index.html       # 인라인
grep -c "!important" src/styles/**/*.css   # 외부

# 목표
# 인라인: 904 → < 200 (S7 단계별 진행)
# 외부: < 50 (이미 9개로 제어됨)
```

### 3-4. 구체 액션 — Step-by-step (예시)

**1주차**: `padding !important` 95개 점검
- DevTools에서 각 element 검사 → `!important` 제거해도 같은 결과인지 확인
- 일괄 sed 금지 — 한 곳씩 검증

**2주차**: `color !important` 96개
**3주차**: `background !important` + `border !important`
**4주차**: `font-*` (가장 어려움 — 한 번에 변경 시 회귀 위험)

각 주마다 visual regression 테스트 통과 필수.

---

## 4. 본 세션에서 작성된 컴포넌트 CSS (S5+S7)

이미 표준 breakpoint와 0~1개 `!important`로 작성됨:

| 파일 | 라인 | breakpoint | !important |
|---|---|---|---|
| `tokens.css` | 252 | — | 0 |
| `base.css` | 227 | 768 | 5 (utility 정당) |
| `components/hero.css` | 152 | 768, 480, landscape | 0 |
| `components/controls.css` | 233 | 768, 380 | 0 |
| `components/typing-area.css` | 173 | 768 | 0 |
| `components/modal.css` | 119 | 768 | 0 |
| `components/stats.css` | 53 | 768 | 0 |
| `components/footer.css` | 65 | 768, standalone | 0 |
| `responsive/mobile.css` | 122 | 1024, 768, 480, 380 | 3 (utility) |

**합계**: 1,396 줄, **!important 8개** (모두 utility 정당). 인라인 904개 → 외부 8개로 99% 감소.

---

## 5. 마이그레이션 체크리스트

각 컴포넌트 마이그레이션 시:

- [ ] 외부 CSS 모듈 import 확인
- [ ] HTML에 새 BEM 클래스 추가 (기존 클래스 유지하면 안전)
- [ ] DevTools Network에서 외부 CSS 200 OK
- [ ] 시각 회귀 5 viewport 확인 (320/480/768/1024/1440)
- [ ] 3 테마 (다크/아이보리/핑크) 모두 정상
- [ ] 인라인 CSS의 해당 컴포넌트 룰 제거
- [ ] 다시 시각 회귀 확인
- [ ] git commit
- [ ] 문제 발견 시 git revert HEAD

---

*마지막 갱신: 2026-04-27*
*S7 산출물: 컴포넌트 CSS 5개 추가 + 정리 가이드*
