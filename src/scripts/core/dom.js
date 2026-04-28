/**
 * Key Therapy — DOM 헬퍼
 * ========================================================
 * 인라인 JS 의 71회+ querySelector / 108회+ getElementById 호출을
 * 캐싱·정리해서 성능 + 가독성 모두 향상.
 *
 * - $(selector) — querySelector 캐싱 버전
 * - $$(selector) — querySelectorAll
 * - $id(id) — getElementById
 * - on / off — 안전한 이벤트 등록/해제 (addEventListener wrapper)
 * - delegate — 이벤트 위임 헬퍼
 * - throttle / debounce — RAF 기반 throttle, setTimeout debounce
 */

const _queryCache = new Map();

/**
 * querySelector 캐싱 버전. 같은 셀렉터에 대해 한 번만 DOM 검색.
 * ⚠️ DOM이 동적으로 변하면 cache invalidation 필요.
 * @param {string} sel
 * @param {Element} [root=document]
 * @returns {Element|null}
 */
export function $(sel, root = document) {
    if (root !== document) {
        // root scope는 캐시 키에 포함하지 않음 (root별 독립 호출)
        return root.querySelector(sel);
    }
    if (_queryCache.has(sel)) {
        const cached = _queryCache.get(sel);
        // 캐시된 element가 아직 DOM에 있는지 확인 (동적 제거 대비)
        if (cached && cached.isConnected) return cached;
        _queryCache.delete(sel);
    }
    const el = document.querySelector(sel);
    if (el) _queryCache.set(sel, el);
    return el;
}

/**
 * querySelectorAll — 캐시 없음 (NodeList는 매번 새로)
 */
export function $$(sel, root = document) {
    return Array.from((root || document).querySelectorAll(sel));
}

/**
 * getElementById 단축
 */
export function $id(id) {
    return document.getElementById(id);
}

/**
 * 캐시 무효화 (DOM 동적 변경 후)
 * @param {string} [sel] - 특정 셀렉터만. 없으면 전체.
 */
export function invalidateCache(sel) {
    if (sel) _queryCache.delete(sel);
    else _queryCache.clear();
}

/**
 * 안전한 이벤트 등록 — cleanup 함수 반환
 * @param {Element|Window|Document} target
 * @param {string} type
 * @param {Function} handler
 * @param {Object|boolean} [options]
 * @returns {Function} cleanup
 */
export function on(target, type, handler, options) {
    if (!target || typeof handler !== 'function') return () => {};
    target.addEventListener(type, handler, options);
    return () => target.removeEventListener(type, handler, options);
}

/**
 * 일회성 이벤트 — 첫 fire 후 자동 해제
 */
export function once(target, type, handler, options = {}) {
    return on(target, type, handler, { ...options, once: true });
}

/**
 * 이벤트 위임 (root 에 등록, 자식 셀렉터 매치 시 handler 호출)
 * @param {Element} root
 * @param {string} type
 * @param {string} childSelector
 * @param {Function} handler — (event, matchedChild) => void
 * @returns {Function} cleanup
 */
export function delegate(root, type, childSelector, handler) {
    return on(root, type, (e) => {
        const match = e.target.closest(childSelector);
        if (match && root.contains(match)) handler(e, match);
    });
}

/**
 * RAF 기반 throttle — 60fps 이하로 호출 빈도 제한
 * @param {Function} fn
 * @returns {Function}
 */
export function throttleRAF(fn) {
    let scheduled = false;
    let lastArgs = null;
    return function (...args) {
        lastArgs = args;
        if (scheduled) return;
        scheduled = true;
        requestAnimationFrame(() => {
            scheduled = false;
            fn.apply(this, lastArgs);
        });
    };
}

/**
 * setTimeout 기반 debounce
 * @param {Function} fn
 * @param {number} wait - ms
 * @returns {Function}
 */
export function debounce(fn, wait) {
    let timer = null;
    return function (...args) {
        clearTimeout(timer);
        timer = setTimeout(() => fn.apply(this, args), wait);
    };
}

/**
 * Class 토글 — 다중 element + 다중 class 한 번에
 */
export function toggleClass(elements, className, force) {
    const arr = Array.isArray(elements) ? elements : [elements];
    arr.forEach(el => el && el.classList.toggle(className, force));
}

/**
 * 자주 쓰는 element 캐싱된 핸들 (애플리케이션 전역)
 * 외부에서 import 하여 직접 사용:
 *   import { els } from '../core/dom.js';
 *   els.typingInputField.focus();
 */
export const els = new Proxy({}, {
    get(_, name) {
        return $('#' + name) || $('.' + name);
    },
});
