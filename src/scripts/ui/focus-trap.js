/**
 * Key Therapy — Focus Trap
 * ========================================================
 * 모달·오버레이 안에 키보드 포커스를 가둠. WCAG 2.1 AA 핵심.
 * helpModal, result-card-modal, asmr-overlay에 적용.
 *
 * 사용 예:
 *   import { trap, untrap } from '../ui/focus-trap.js';
 *
 *   // 모달 열 때
 *   const release = trap(modalEl, {
 *     onEscape: () => closeModal(),
 *     initialFocus: '.modal__btn',  // 열릴 때 포커스 받을 element selector
 *     restoreFocus: true,            // 닫힐 때 이전 포커스로 복귀
 *   });
 *
 *   // 모달 닫을 때
 *   release();
 *
 * 또는 한 번에:
 *   trap(modalEl, { onEscape: closeModal });
 *   // ...
 *   untrap(modalEl);
 */

/** 포커스 가능한 element selector — WAI-ARIA 권장 */
const FOCUSABLE_SELECTOR = [
    'a[href]',
    'button:not([disabled])',
    'input:not([disabled]):not([type="hidden"])',
    'select:not([disabled])',
    'textarea:not([disabled])',
    '[tabindex]:not([tabindex="-1"])',
    '[contenteditable="true"]',
    'audio[controls]',
    'video[controls]',
].join(',');

const _trapsByElement = new WeakMap();

/**
 * element 안에서 포커스 가능한 자손 목록
 */
function getFocusableElements(root) {
    return Array.from(root.querySelectorAll(FOCUSABLE_SELECTOR))
        .filter(el => {
            // 화면에 보이는 element만
            return el.offsetParent !== null
                || el === document.activeElement
                || el.getClientRects().length > 0;
        });
}

/**
 * Focus trap 활성화
 * @param {Element} container - trap 대상 (모달·오버레이 root)
 * @param {Object} [options]
 * @param {Function} [options.onEscape] - Esc 키 처리
 * @param {string|Element} [options.initialFocus] - 초기 포커스 (selector 또는 element)
 * @param {boolean} [options.restoreFocus=true] - 닫을 때 이전 element로 포커스 복귀
 * @returns {Function} release - 호출 시 trap 해제
 */
export function trap(container, options = {}) {
    if (!container) return () => {};

    // 이미 trap된 element면 기존 release 반환
    if (_trapsByElement.has(container)) {
        return _trapsByElement.get(container).release;
    }

    const {
        onEscape,
        initialFocus,
        restoreFocus = true,
    } = options;

    // 이전 포커스 element 저장
    const previouslyFocused = restoreFocus ? document.activeElement : null;

    // Tab 키 핸들러
    function handleKeydown(e) {
        // Esc — onEscape 콜백 호출
        if (e.key === 'Escape' && typeof onEscape === 'function') {
            e.preventDefault();
            onEscape(e);
            return;
        }
        if (e.key !== 'Tab') return;

        const focusables = getFocusableElements(container);
        if (focusables.length === 0) {
            // trap 대상 안에 포커스 가능 element 없음 → container에 포커스
            e.preventDefault();
            container.focus();
            return;
        }
        const first = focusables[0];
        const last = focusables[focusables.length - 1];
        const active = document.activeElement;

        // Shift+Tab on first → wrap to last
        if (e.shiftKey && active === first) {
            e.preventDefault();
            last.focus();
        }
        // Tab on last → wrap to first
        else if (!e.shiftKey && active === last) {
            e.preventDefault();
            first.focus();
        }
        // 컨테이너 외부에 포커스가 있으면 첫 element로 강제
        else if (!container.contains(active)) {
            e.preventDefault();
            first.focus();
        }
    }

    // mousedown handler — 외부 클릭 시 trap 유지
    function handleMousedown(e) {
        if (!container.contains(e.target)) {
            // 외부 클릭은 무시 — 사용자가 의도적으로 닫고자 하면 모달의 backdrop이 처리
        }
    }

    // 초기 포커스
    let initialFocusEl = null;
    if (initialFocus) {
        if (typeof initialFocus === 'string') {
            initialFocusEl = container.querySelector(initialFocus);
        } else if (initialFocus instanceof Element) {
            initialFocusEl = initialFocus;
        }
    }
    if (!initialFocusEl) {
        const focusables = getFocusableElements(container);
        initialFocusEl = focusables[0] || container;
    }
    // container 자체에 포커스를 받으려면 tabindex="-1" 필요
    if (initialFocusEl === container && !container.hasAttribute('tabindex')) {
        container.setAttribute('tabindex', '-1');
    }
    // 다음 프레임에 포커스 (모달 transition 이후)
    requestAnimationFrame(() => {
        try { initialFocusEl.focus({ preventScroll: false }); } catch (_) {}
    });

    // 이벤트 등록
    document.addEventListener('keydown', handleKeydown, true);
    document.addEventListener('mousedown', handleMousedown, true);

    // ARIA — 모달 외부 콘텐츠 inert
    const inertTargets = [];
    Array.from(document.body.children).forEach(child => {
        if (!child.contains(container) && child !== container) {
            if (!child.hasAttribute('aria-hidden')) {
                child.setAttribute('aria-hidden', 'true');
                inertTargets.push(child);
            }
        }
    });

    // release 함수
    function release() {
        document.removeEventListener('keydown', handleKeydown, true);
        document.removeEventListener('mousedown', handleMousedown, true);
        inertTargets.forEach(el => el.removeAttribute('aria-hidden'));
        if (restoreFocus && previouslyFocused && typeof previouslyFocused.focus === 'function') {
            try { previouslyFocused.focus({ preventScroll: true }); } catch (_) {}
        }
        _trapsByElement.delete(container);
    }

    _trapsByElement.set(container, { release });
    return release;
}

/**
 * 명시적 trap 해제 (release 함수를 잃어버린 경우)
 */
export function untrap(container) {
    const entry = _trapsByElement.get(container);
    if (entry && typeof entry.release === 'function') {
        entry.release();
    }
}

/**
 * 현재 trap 활성화 여부
 */
export function isTrapped(container) {
    return _trapsByElement.has(container);
}
