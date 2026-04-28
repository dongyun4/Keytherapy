/**
 * Key Therapy — Keyboard Navigation 헬퍼
 * ========================================================
 * 화살표 키·Home·End 등으로 그룹 내 탐색 (radio·tab·toolbar 패턴).
 * WCAG 2.1.1 (Keyboard) + 2.4.3 (Focus Order) 보강.
 */

import { on } from '../core/dom.js';

/**
 * 그룹 내 화살표 키 이동 — toolbar / tab / radio group
 * @param {Element} container - 그룹 root
 * @param {Object} [options]
 * @param {string} [options.itemSelector='[role="button"], button'] - 자식 element selector
 * @param {'horizontal'|'vertical'|'both'} [options.orientation='horizontal']
 * @param {boolean} [options.wrap=true] - 끝에서 처음으로 wrap
 * @returns {Function} cleanup
 */
export function arrowNavigation(container, options = {}) {
    if (!container) return () => {};
    const {
        itemSelector = '[role="button"], button:not([disabled])',
        orientation = 'horizontal',
        wrap = true,
    } = options;

    function getItems() {
        return Array.from(container.querySelectorAll(itemSelector))
            .filter(el => !el.disabled && el.tabIndex !== -1);
    }

    return on(container, 'keydown', (e) => {
        const items = getItems();
        if (items.length === 0) return;

        const currentIndex = items.indexOf(document.activeElement);
        if (currentIndex === -1) return;

        let nextIndex = currentIndex;

        const isHorizontal = orientation !== 'vertical';
        const isVertical = orientation !== 'horizontal';

        switch (e.key) {
            case 'ArrowRight':
                if (!isHorizontal) return;
                nextIndex = currentIndex + 1;
                break;
            case 'ArrowLeft':
                if (!isHorizontal) return;
                nextIndex = currentIndex - 1;
                break;
            case 'ArrowDown':
                if (!isVertical) return;
                nextIndex = currentIndex + 1;
                break;
            case 'ArrowUp':
                if (!isVertical) return;
                nextIndex = currentIndex - 1;
                break;
            case 'Home':
                nextIndex = 0;
                break;
            case 'End':
                nextIndex = items.length - 1;
                break;
            default:
                return;
        }

        // wrap 처리
        if (wrap) {
            if (nextIndex < 0) nextIndex = items.length - 1;
            else if (nextIndex >= items.length) nextIndex = 0;
        } else {
            nextIndex = Math.max(0, Math.min(nextIndex, items.length - 1));
        }

        if (nextIndex !== currentIndex) {
            e.preventDefault();
            items[nextIndex].focus();
        }
    });
}

/**
 * Roving tabindex 패턴 — 그룹 내 단 1개 element만 tabIndex=0,
 * 나머지는 tabIndex=-1. 화살표로 이동, Tab으로 그룹 진/출.
 * @param {Element} container
 * @param {string} [itemSelector]
 */
export function rovingTabindex(container, itemSelector = '[role="button"], button:not([disabled])') {
    if (!container) return () => {};

    function update() {
        const items = Array.from(container.querySelectorAll(itemSelector));
        items.forEach((el, idx) => {
            el.tabIndex = idx === 0 ? 0 : -1;
        });
    }
    update();

    const cleanups = [];
    cleanups.push(on(container, 'focusin', (e) => {
        // 포커스 받은 element의 tabIndex=0, 나머지는 -1
        const items = Array.from(container.querySelectorAll(itemSelector));
        items.forEach(el => { el.tabIndex = el === e.target ? 0 : -1; });
    }));
    cleanups.push(arrowNavigation(container, { itemSelector }));

    return () => cleanups.forEach(off => off());
}

/**
 * Esc 키로 닫기 — 모달·드롭다운 공통 패턴
 * @param {Function} onEscape
 * @param {Object} [options]
 * @param {Element} [options.target=document]
 * @returns {Function} cleanup
 */
export function onEscape(onEscape, options = {}) {
    const { target = document } = options;
    return on(target, 'keydown', (e) => {
        if (e.key === 'Escape' || e.key === 'Esc') {
            onEscape(e);
        }
    });
}
