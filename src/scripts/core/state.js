/**
 * Key Therapy — 단일 상태 store
 * ========================================================
 * 기존 인라인 JS의 195개+ 전역 var(`currentMode`, `linesToPractice` 등)를
 * 하나의 reactive store로 통합. Pub/Sub 기반.
 *
 * 사용 예:
 *   import { state, on, get, set } from '../core/state.js';
 *
 *   // 읽기
 *   const lines = get('linesToPractice');
 *
 *   // 쓰기 (자동으로 listener에게 알림)
 *   set('currentMode', 'asmr');
 *
 *   // 변경 구독 (cleanup 함수 반환)
 *   const off = on('currentMode', (newVal, oldVal) => {
 *     console.log('Mode changed:', oldVal, '→', newVal);
 *   });
 *   // 구독 해제: off();
 *
 * 마이그레이션 가이드: state.js 의 마지막 섹션 참조.
 */

const _state = Object.create(null);
const _listeners = new Map(); // key → Set<callback>
const _allListeners = new Set(); // key 무관 모든 변경 구독

/**
 * 초기 상태 — 인라인 JS 의 전역 변수들을 여기로 이주
 * (현재 빈 state로 시작. 점진 마이그레이션)
 */
const initialState = {
    // ─── 연습 모드 ───
    currentMode: 'short',          // 'short' | 'long' | 'freestyle' | 'asmr' | 'game'
    practiceType: 'short',
    currentLanguage: 'kor',
    linesToPractice: [],
    currentDisplayLineIndex: 0,

    // ─── 토글 ───
    soundEnabled: false,
    highlightEnabled: true,
    statsVisible: true,
    keyboardGuideEnabled: false,
    layoutCollapsed: false,

    // ─── 통계 ───
    sessionStartTime: null,
    sessionTotalCorrectChars: 0,
    sessionTotalValidChars: 0,
    sessionMaxSpeed: 0,
    totalLifetimeChars: 0,

    // ─── 게임 ───
    currentGameType: null,         // null | 'rainfall' | 'letterBlockBattle' | 'giantBattle' | 'wordRush'

    // ─── 테마·앰비언스 ───
    currentTheme: 'dark',          // 'dark' | 'light' | 'pink'
    currentAmbience: 'glow',       // glow / candle / streetlamp / firefly / sunbeam / ...

    // ─── ASMR ───
    asmrActive: false,
    asmrLineIdx: 0,
};

// Object.assign으로 초기값 복사
Object.assign(_state, initialState);

/**
 * 값 읽기
 * @param {string} key
 * @returns {*}
 */
export function get(key) {
    return _state[key];
}

/**
 * 값 쓰기 + listener 호출
 * @param {string} key
 * @param {*} value
 */
export function set(key, value) {
    const oldValue = _state[key];
    if (oldValue === value) return; // 동일 값은 무시 (불필요한 알림 차단)
    _state[key] = value;
    // key별 리스너 알림
    const ls = _listeners.get(key);
    if (ls) {
        for (const cb of ls) {
            try { cb(value, oldValue, key); } catch (e) { console.warn('[state]', e); }
        }
    }
    // 전체 리스너 알림
    for (const cb of _allListeners) {
        try { cb(value, oldValue, key); } catch (e) { console.warn('[state]', e); }
    }
}

/**
 * 여러 키 동시 갱신 (배치)
 * @param {Object} patch - { key1: value1, key2: value2 }
 */
export function update(patch) {
    for (const [k, v] of Object.entries(patch)) set(k, v);
}

/**
 * 변경 구독
 * @param {string} key - 구독할 키. '*' 이면 전체 변경 구독
 * @param {Function} callback - (newVal, oldVal, key) => void
 * @returns {Function} cleanup — 호출 시 구독 해제
 */
export function on(key, callback) {
    if (typeof callback !== 'function') return () => {};
    if (key === '*') {
        _allListeners.add(callback);
        return () => _allListeners.delete(callback);
    }
    if (!_listeners.has(key)) _listeners.set(key, new Set());
    _listeners.get(key).add(callback);
    return () => {
        const ls = _listeners.get(key);
        if (ls) ls.delete(callback);
    };
}

/**
 * 전체 state 스냅샷 (디버깅용)
 * @returns {Object} state의 얕은 복사
 */
export function snapshot() {
    return { ..._state };
}

/**
 * 리스너 모두 제거 (테스트 환경 cleanup용)
 */
export function clearAllListeners() {
    _listeners.clear();
    _allListeners.clear();
}

/**
 * state 객체 직접 export (읽기 전용 접근용 — 절대 직접 mutation 금지)
 * @deprecated 가능하면 get/set 사용
 */
export const state = new Proxy(_state, {
    set() {
        console.warn('[state] Direct mutation is forbidden. Use set() instead.');
        return false;
    },
});

/* ============================================================
   마이그레이션 가이드 (인라인 → store)

   기존 인라인 패턴:
     let currentMode = 'short';
     // ... 다른 곳에서:
     currentMode = 'asmr';
     someFunction(currentMode);

   1단계 — 읽기/쓰기를 함수 호출로 변경:
     import { get, set, on } from '../core/state.js';
     set('currentMode', 'asmr');
     someFunction(get('currentMode'));

   2단계 — 모드 변경 시 부수 효과를 listener로:
     // 기존: currentMode 변경 후 곳곳에서 if 분기로 처리
     if (currentMode === 'asmr') openAsmr();
     // 신규: 한 번 등록하면 자동
     on('currentMode', (mode) => {
       if (mode === 'asmr') openAsmr();
       else if (mode === 'game') openGame();
     });

   3단계 — 모듈 unmount 시 listener 정리:
     class MyComponent {
       constructor() {
         this._cleanups = [
           on('currentMode', this.handleModeChange),
           on('soundEnabled', this.handleSoundToggle),
         ];
       }
       destroy() {
         this._cleanups.forEach(off => off());
       }
     }

   ⚠️ 주의:
   - 객체·배열 값은 immutable로 다뤄야 함 (참조 같으면 변경 알림 무시).
     ❌ const arr = get('linesToPractice'); arr.push(x);
     ✅ set('linesToPractice', [...get('linesToPractice'), x]);
   - 무한 루프 주의: listener 안에서 같은 키 set() 시 가드 필요.
   ============================================================ */
