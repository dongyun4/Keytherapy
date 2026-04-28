/**
 * Key Therapy — 단일 RAF Scheduler
 * ========================================================
 * 인라인 JS 의 4개 게임 + 앰비언스 RAF를 1개로 통합.
 * 백그라운드 탭 시 자동 pause, 복귀 시 resume.
 *
 * 사용 예:
 *   import { add, remove, pauseAll, resumeAll } from '../core/raf-scheduler.js';
 *
 *   const myTask = (now) => {
 *     // 매 프레임 호출 (60fps)
 *     // now: performance.now()
 *   };
 *   add(myTask);
 *
 *   // 작업 끝나면:
 *   remove(myTask);
 */

const _tasks = new Set();
let _running = false;
let _rafId = null;
let _paused = false;

function _tick(now) {
    if (_paused) {
        _running = false;
        _rafId = null;
        return;
    }
    for (const task of _tasks) {
        try { task(now); } catch (e) { console.warn('[RAFScheduler] task failed:', e); }
    }
    if (_tasks.size > 0) {
        _rafId = requestAnimationFrame(_tick);
    } else {
        _running = false;
        _rafId = null;
    }
}

/**
 * task 등록
 * @param {Function} task - (now: number) => void
 * @returns {Function} cleanup — 호출 시 task 제거
 */
export function add(task) {
    if (typeof task !== 'function') return () => {};
    _tasks.add(task);
    if (!_running && !_paused) {
        _running = true;
        _rafId = requestAnimationFrame(_tick);
    }
    return () => remove(task);
}

/**
 * task 제거
 */
export function remove(task) {
    _tasks.delete(task);
}

/**
 * 모두 일시정지 (백그라운드 탭 진입 시)
 * task는 유지되며 resumeAll 호출 시 즉시 재개
 */
export function pauseAll() {
    _paused = true;
    if (_rafId !== null) {
        cancelAnimationFrame(_rafId);
        _rafId = null;
        _running = false;
    }
}

/**
 * 모두 재개
 */
export function resumeAll() {
    if (!_paused) return;
    _paused = false;
    if (_tasks.size > 0 && !_running) {
        _running = true;
        _rafId = requestAnimationFrame(_tick);
    }
}

/**
 * 모든 task 제거 + RAF cancel
 */
export function clear() {
    _tasks.clear();
    if (_rafId !== null) cancelAnimationFrame(_rafId);
    _rafId = null;
    _running = false;
}

/**
 * 디버깅 — 현재 등록된 task 수
 */
export function size() {
    return _tasks.size;
}

/**
 * visibility 자동 연동 — 페이지 hidden 시 pause, visible 시 resume
 * 모듈 로드 시 1회 자동 호출됨. 수동 해제 가능.
 */
function _bindVisibility() {
    if (typeof document === 'undefined') return () => {};
    const handler = () => {
        if (document.hidden) pauseAll();
        else resumeAll();
    };
    document.addEventListener('visibilitychange', handler, { passive: true });
    return () => document.removeEventListener('visibilitychange', handler);
}
const _unbind = _bindVisibility();

/**
 * 자동 visibility 연동 해제 (테스트용)
 */
export function unbindVisibility() {
    _unbind();
}
