/**
 * Key Therapy — Web Vitals 모니터링 (LCP/INP/CLS/FCP/TTFB)
 * ========================================================
 * 의존성 없이 PerformanceObserver 기반으로 핵심 지표 측정.
 * Sentry·Vercel Analytics·자체 백엔드 어디든 보낼 수 있도록 콜백 패턴.
 *
 * 사용:
 *   import { observeVitals } from './core/web-vitals.js';
 *
 *   observeVitals((metric) => {
 *     // metric: { name, value, rating, delta, id }
 *     // ratings: 'good' | 'needs-improvement' | 'poor'
 *     console.log(metric);
 *     // 또는 백엔드로 전송:
 *     navigator.sendBeacon('/api/vitals', JSON.stringify(metric));
 *   });
 *
 * 임계값 (Google 권장):
 *   LCP : good < 2.5s | poor > 4.0s
 *   INP : good < 200ms | poor > 500ms
 *   CLS : good < 0.1 | poor > 0.25
 *   FCP : good < 1.8s | poor > 3.0s
 *   TTFB: good < 800ms | poor > 1800ms
 */

const THRESHOLDS = {
    LCP:  { good: 2500, poor: 4000 },
    INP:  { good: 200,  poor: 500 },
    CLS:  { good: 0.1,  poor: 0.25 },
    FCP:  { good: 1800, poor: 3000 },
    TTFB: { good: 800,  poor: 1800 },
};

function rate(name, value) {
    const t = THRESHOLDS[name];
    if (!t) return 'unknown';
    if (value <= t.good) return 'good';
    if (value <= t.poor) return 'needs-improvement';
    return 'poor';
}

function uid() {
    return 'kt-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 8);
}

function emit(name, value, callback) {
    try {
        callback({
            name,
            value: Math.round(value * 1000) / 1000,
            rating: rate(name, value),
            id: uid(),
            timestamp: Date.now(),
        });
    } catch (e) {
        console.warn('[web-vitals] callback failed:', e);
    }
}

/**
 * 모든 핵심 지표 관찰 시작
 * @param {Function} callback - (metric) => void
 */
export function observeVitals(callback) {
    if (typeof callback !== 'function') return;
    if (typeof PerformanceObserver === 'undefined') return;

    /* ─── LCP — Largest Contentful Paint ─── */
    try {
        const lcpObserver = new PerformanceObserver((entries) => {
            const list = entries.getEntries();
            const last = list[list.length - 1];
            if (last) emit('LCP', last.startTime, callback);
        });
        lcpObserver.observe({ type: 'largest-contentful-paint', buffered: true });
        // page hide 시 최종 값 보고
        addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'hidden') lcpObserver.takeRecords?.();
        }, { once: true });
    } catch (_) {}

    /* ─── INP — Interaction to Next Paint ─── */
    try {
        let maxDuration = 0;
        const inpObserver = new PerformanceObserver((entries) => {
            for (const entry of entries.getEntries()) {
                if (entry.duration > maxDuration) {
                    maxDuration = entry.duration;
                    emit('INP', maxDuration, callback);
                }
            }
        });
        inpObserver.observe({ type: 'event', buffered: true, durationThreshold: 16 });
    } catch (_) {}

    /* ─── CLS — Cumulative Layout Shift ─── */
    try {
        let clsValue = 0;
        const clsObserver = new PerformanceObserver((entries) => {
            for (const entry of entries.getEntries()) {
                if (!entry.hadRecentInput) {
                    clsValue += entry.value;
                    emit('CLS', clsValue, callback);
                }
            }
        });
        clsObserver.observe({ type: 'layout-shift', buffered: true });
    } catch (_) {}

    /* ─── FCP — First Contentful Paint ─── */
    try {
        const fcpObserver = new PerformanceObserver((entries) => {
            for (const entry of entries.getEntries()) {
                if (entry.name === 'first-contentful-paint') {
                    emit('FCP', entry.startTime, callback);
                    fcpObserver.disconnect();
                }
            }
        });
        fcpObserver.observe({ type: 'paint', buffered: true });
    } catch (_) {}

    /* ─── TTFB — Time to First Byte ─── */
    try {
        const navEntries = performance.getEntriesByType('navigation');
        if (navEntries.length > 0) {
            const ttfb = navEntries[0].responseStart - navEntries[0].requestStart;
            emit('TTFB', ttfb, callback);
        }
    } catch (_) {}
}

/**
 * sendBeacon 으로 vitals 전송 (페이지 이탈 시에도 안전)
 * @param {string} endpoint
 * @returns {Function} - observeVitals 콜백으로 전달
 */
export function beaconReporter(endpoint) {
    return (metric) => {
        try {
            const body = JSON.stringify(metric);
            if (navigator.sendBeacon) {
                navigator.sendBeacon(endpoint, body);
            } else {
                fetch(endpoint, { method: 'POST', body, keepalive: true });
            }
        } catch (_) {}
    };
}

/**
 * console 로 print (개발 시 디버깅)
 */
export function consoleReporter(metric) {
    const colors = { good: '#7ab08a', 'needs-improvement': '#d4a574', poor: '#c97474' };
    const color = colors[metric.rating] || '#888';
    console.log(
        `%c${metric.name} %c${metric.value}ms %c[${metric.rating}]`,
        'font-weight: bold;',
        'color: ' + color + ';',
        'color: #888; font-size: 0.85em;'
    );
}
