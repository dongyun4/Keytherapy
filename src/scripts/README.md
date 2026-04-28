# Key Therapy — JS 모듈 구조

> S6 산출물. 14k 줄 인라인 JS의 점진 분리를 위한 핵심 유틸 모듈 + 가이드.
> 실제 분리는 사용자 환경(Vite 셋업 후)에서 진행.

## 디렉토리 구조

```
src/scripts/
├── index.js              ← 진입점 (앞으로 추가)
├── core/
│   ├── state.js          ← 단일 store (전역 var → namespaced)
│   ├── dom.js            ← querySelector 캐싱·이벤트 헬퍼
│   ├── raf-scheduler.js  ← 단일 RAF 통합 (DEF-001)
│   └── audio-engine.js   ← (다음 단계)
├── util/
│   ├── escape.js         ← XSS 방지 (DEF-015 단위 테스트 짝)
│   └── measure.js        ← Canvas 측정 (모바일 한 줄 fit)
├── modes/                ← (다음 단계)
│   ├── short-practice.js
│   ├── long-practice.js
│   ├── freestyle.js
│   ├── asmr.js
│   └── games/
│       ├── rainfall.js
│       ├── letter-block.js
│       ├── giant-battle.js
│       └── word-rush.js
└── ui/                   ← (다음 단계)
    ├── ambience-engine.js
    ├── stats.js
    ├── popovers.js
    └── result-card.js
```

## 의존성 그래프

```
                   ┌──────────────────┐
                   │   index.js       │  진입점
                   └────────┬─────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
  ┌──────────┐       ┌─────────────┐      ┌──────────┐
  │ core/    │       │ modes/      │      │ ui/      │
  │ - state  │◄──────│ - short     │─────▶│ - stats  │
  │ - dom    │       │ - long      │      │ - amb    │
  │ - raf    │◄──────│ - asmr      │─────▶│ - popov  │
  └────┬─────┘       │ - freestyle │      └──────────┘
       │             │ - games/*   │
       │             └─────┬───────┘
       │                   │
       ▼                   ▼
  ┌──────────────────────────┐
  │ util/                    │
  │ - escape  (XSS)          │
  │ - measure (canvas fit)   │
  └──────────────────────────┘
```

**핵심 원칙**: `util` ← `core` ← `modes`/`ui` 단방향. 상위 모듈이 하위 모듈을 import하되, 역방향 절대 금지(순환 참조 위험).

## 현재 작성 완료 (본 세션)

| 모듈 | 라인 | 책임 |
|---|---|---|
| `core/state.js` | 168 | Pub/Sub 단일 store. 195개+ 전역 var를 1개 namespace로 |
| `core/dom.js` | 144 | $·$$·$id 캐싱, on/off, delegate, throttleRAF, debounce |
| `core/raf-scheduler.js` | 100 | 단일 RAF, visibilitychange 자동 pause/resume |
| `util/escape.js` | 56 | escapeHtml, sanitizeFilename, safeCompare |
| `util/measure.js` | 91 | measureTextWidth, fitToWidth, LRU 캐시 |
| `tests/escape.spec.js` | 102 | 단위 테스트 (DEF-015 회귀 방지) |

**총 661 줄** (인라인 JS 약 7,500줄 중 핵심 유틸만 추출)

## 단위 테스트 실행

```bash
npm run test           # watch mode
npm run test:run       # CI mode (1회)
npm run test -- --ui   # Vitest UI (브라우저)
```

기대: 모든 테스트 PASS. 실패 시 escape 함수 회귀 가능성 — 즉시 수정.

## 마이그레이션 패턴 (인라인 → 모듈)

### Before — 인라인 14k HTML 안

```html
<script>
  let currentMode = 'short';        // 전역 var
  let linesToPractice = [];         // 전역 var

  function activateAsmr() {
    currentMode = 'asmr';
    document.body.classList.add('asmr-mode-active');
    // ...
  }
</script>
```

### After — 모듈 분리

```js
// src/scripts/modes/asmr.js
import { set, get, on } from '../core/state.js';
import { $id, on as listen } from '../core/dom.js';

export function activate() {
  set('currentMode', 'asmr');
  set('asmrActive', true);
  document.body.classList.add('asmr-mode-active');
}

// 모드 변경 자동 감지
on('currentMode', (mode) => {
  if (mode !== 'asmr') {
    document.body.classList.remove('asmr-mode-active');
  }
});
```

```js
// src/scripts/index.js (진입점)
import { activate as activateAsmr } from './modes/asmr.js';
import { $id, on } from './core/dom.js';

document.addEventListener('DOMContentLoaded', () => {
  on($id('asmrModeBtn'), 'click', activateAsmr);
});
```

## 단계적 분리 권장 순서

| 우선순위 | 모듈 | 분리 난이도 | 영향도 |
|---|---|---|---|
| 1 | ✅ `util/escape.js` | 낮음 | 높음 (보안) |
| 2 | ✅ `util/measure.js` | 낮음 | 중 (모바일 fit) |
| 3 | ✅ `core/state.js` | 중 | 매우 높음 (전역 정리) |
| 4 | ✅ `core/dom.js` | 낮음 | 중 (성능) |
| 5 | ✅ `core/raf-scheduler.js` | 중 | 높음 (퍼포먼스) |
| 6 | ⏳ `core/audio-engine.js` | 중 | 중 |
| 7 | ⏳ `modes/freestyle.js` | 낮음 | 낮음 (자체 완결) |
| 8 | ⏳ `modes/asmr.js` | 중 | 중 (오버레이 복잡) |
| 9 | ⏳ `modes/short-practice.js` `long-practice.js` | 중 | 중 |
| 10 | ⏳ `modes/games/*` | 높음 | 매우 높음 (게임 로직 복잡) |
| 11 | ⏳ `ui/ambience-engine.js` | 중 | 낮음 |
| 12 | ⏳ `ui/stats.js` `popovers.js` `result-card.js` | 낮음 | 낮음 |

## Memory Leak 방지 패턴

각 모듈에 `init` / `destroy` 페어 권장:

```js
// modes/asmr.js
const cleanups = [];

export function init() {
  cleanups.push(
    listen($id('asmrCloseBtn'), 'click', close),
    listen(window, 'keydown', handleKeydown),
    on('currentMode', handleModeChange),     // state.js subscriber
  );
}

export function destroy() {
  cleanups.forEach(off => off());
  cleanups.length = 0;
}
```

## Vite import 순서 (`src/scripts/index.js`)

```js
// 1. Foundation — 부수 효과 없음
import { state, set, get, on } from './core/state.js';
import { $, $$, $id, on as listen, delegate } from './core/dom.js';
import { add as rafAdd, remove as rafRemove } from './core/raf-scheduler.js';
import { escapeHtml, sanitizeFilename } from './util/escape.js';
import { measureTextWidth, fitToWidth } from './util/measure.js';

// 2. Modes — 부수 효과 (button click 등록)
import { init as initShort } from './modes/short-practice.js';
import { init as initAsmr } from './modes/asmr.js';
// ...

// 3. UI
import { init as initAmbience } from './ui/ambience-engine.js';
// ...

// 4. 시작
document.addEventListener('DOMContentLoaded', () => {
  initShort();
  initAsmr();
  initAmbience();
});
```

## 향후 작업 (S7+)

- **S7 (반응형·!important 정리)**: 인라인 CSS 점진 제거 시 새 컴포넌트 CSS도 함께 활성화
- **S8 (접근성)**: Focus trap·키보드 nav 모듈을 `ui/`에 추가
- **S9 (PWA·모니터링)**: Service Worker 등록을 `core/sw-register.js`에
- **S10 (회귀 테스트)**: Playwright 시나리오 30개 + Vitest 커버리지 70%+

---

*마지막 갱신: 2026-04-27*
*S6 산출물: 5개 모듈 + 1개 테스트 + 가이드 (661 줄)*
*기준 보고서: `KEYTHERAPY_SENIOR_REVIEW.md`*
