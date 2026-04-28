/**
 * Key Therapy — Service Worker 등록
 * ========================================================
 * /sw.js 등록 + 새 버전 감지 + 사용자 새로고침 안내.
 *
 * 사용:
 *   import { registerSW } from './core/sw-register.js';
 *   registerSW();
 */

const SW_PATH = '/sw.js';
const SW_SCOPE = '/';

/**
 * Service Worker 등록
 * @param {Object} [options]
 * @param {Function} [options.onUpdate] - 새 버전 감지 시 콜백
 * @param {Function} [options.onActivate] - 활성화 완료 시 콜백
 * @returns {Promise<ServiceWorkerRegistration|null>}
 */
export async function registerSW(options = {}) {
    if (!('serviceWorker' in navigator)) {
        return null;
    }

    // 개발 환경에서는 비활성화 (Vite HMR 충돌 방지)
    if (location.hostname === 'localhost' || location.hostname === '127.0.0.1') {
        // SW 이미 등록돼 있으면 해제 (개발 시 캐시 문제 방지)
        try {
            const regs = await navigator.serviceWorker.getRegistrations();
            for (const reg of regs) await reg.unregister();
        } catch (_) {}
        return null;
    }

    try {
        const registration = await navigator.serviceWorker.register(SW_PATH, {
            scope: SW_SCOPE,
            updateViaCache: 'none', // 매번 sw.js를 fresh fetch
        });

        // 새 SW 발견 시
        registration.addEventListener('updatefound', () => {
            const installing = registration.installing;
            if (!installing) return;
            installing.addEventListener('statechange', () => {
                if (
                    installing.state === 'installed' &&
                    navigator.serviceWorker.controller
                ) {
                    // 기존 SW가 있는데 새 SW가 설치 완료 → 업데이트 가능
                    if (typeof options.onUpdate === 'function') {
                        options.onUpdate(registration);
                    } else {
                        showUpdateBanner(registration);
                    }
                }
            });
        });

        // 활성화된 SW가 controller로 바뀌면 (skipWaiting 후)
        navigator.serviceWorker.addEventListener('controllerchange', () => {
            if (typeof options.onActivate === 'function') {
                options.onActivate();
            }
        });

        return registration;
    } catch (err) {
        console.warn('[SW] registration failed:', err);
        return null;
    }
}

/**
 * 새 버전 알림 배너 (기본 UI)
 */
function showUpdateBanner(registration) {
    const banner = document.createElement('div');
    banner.setAttribute('role', 'status');
    banner.setAttribute('aria-live', 'polite');
    banner.style.cssText = `
        position: fixed;
        bottom: 24px;
        left: 50%;
        transform: translateX(-50%);
        background: rgba(20, 18, 16, 0.92);
        color: #f5dfb3;
        padding: 12px 22px;
        border-radius: 999px;
        font-size: 14px;
        z-index: 9999;
        backdrop-filter: blur(12px);
        box-shadow: 0 10px 30px rgba(0,0,0,0.4);
        display: flex;
        align-items: center;
        gap: 12px;
        font-family: 'Pretendard', sans-serif;
    `;
    banner.innerHTML = `
        <span>새 버전이 준비되었습니다.</span>
        <button style="
            background: rgba(212, 175, 122, 0.2);
            border: 1px solid rgba(212, 175, 122, 0.4);
            color: #f5dfb3;
            padding: 6px 14px;
            border-radius: 999px;
            cursor: pointer;
            font: inherit;
        " id="kt-sw-reload-btn">새로고침</button>
    `;
    document.body.appendChild(banner);
    document.getElementById('kt-sw-reload-btn').addEventListener('click', () => {
        const waiting = registration.waiting;
        if (waiting) waiting.postMessage({ type: 'SKIP_WAITING' });
        // controllerchange에서 자동 reload
        navigator.serviceWorker.addEventListener('controllerchange', () => {
            window.location.reload();
        }, { once: true });
    });
}

/**
 * SW 등록 해제 (디버깅·rollback)
 */
export async function unregisterSW() {
    if (!('serviceWorker' in navigator)) return false;
    const regs = await navigator.serviceWorker.getRegistrations();
    let success = true;
    for (const reg of regs) {
        const ok = await reg.unregister();
        if (!ok) success = false;
    }
    return success;
}
