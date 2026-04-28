/**
 * Key Therapy — Service Worker
 * ========================================================
 * 정적 자산 캐싱 + 오프라인 폴백.
 * 전략:
 *  - HTML : Network-first (최신 콘텐츠 우선, 실패 시 캐시)
 *  - Static (CSS·JS·SVG·font) : Stale-while-revalidate (캐시 우선 + 백그라운드 갱신)
 *  - 외부 CDN (Pretendard·FontAwesome) : Cache-first
 *
 * 버전 변경 시 CACHE_VERSION만 bump 하면 자동으로 구캐시 정리.
 */

const CACHE_VERSION = 'kt-v1';
const STATIC_CACHE = `${CACHE_VERSION}-static`;
const RUNTIME_CACHE = `${CACHE_VERSION}-runtime`;
const FONT_CACHE = `${CACHE_VERSION}-fonts`;

// 사전 캐싱 — 핵심 셸 (오프라인 진입 가능하게)
const PRECACHE_URLS = [
    '/',
    '/index.html',
    '/manifest.json',
    '/og-cover.svg',
];

// 모든 캐시 prefix — 구버전 정리에 사용
const CACHE_PREFIX = 'kt-';

/* ─────────────── INSTALL ─────────────── */
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(STATIC_CACHE).then((cache) => {
            return cache.addAll(PRECACHE_URLS).catch((err) => {
                console.warn('[SW] Precache failed:', err);
            });
        }).then(() => self.skipWaiting())
    );
});

/* ─────────────── ACTIVATE ─────────────── */
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) => {
            return Promise.all(
                keys
                    .filter((k) => k.startsWith(CACHE_PREFIX) && !k.startsWith(CACHE_VERSION))
                    .map((k) => caches.delete(k))
            );
        }).then(() => self.clients.claim())
    );
});

/* ─────────────── FETCH ─────────────── */
self.addEventListener('fetch', (event) => {
    const { request } = event;

    // GET 요청만 처리
    if (request.method !== 'GET') return;

    const url = new URL(request.url);

    // 외부 CDN — Cache-first (Pretendard·FontAwesome·Google Fonts)
    if (
        url.hostname === 'cdn.jsdelivr.net' ||
        url.hostname === 'cdnjs.cloudflare.com' ||
        url.hostname === 'fonts.googleapis.com' ||
        url.hostname === 'fonts.gstatic.com'
    ) {
        event.respondWith(cacheFirst(request, FONT_CACHE));
        return;
    }

    // Vercel insights — 무시 (캐시 안 함)
    if (url.pathname.startsWith('/_vercel/')) return;

    // 같은 도메인 — 자산 타입별
    if (url.origin === self.location.origin) {
        // HTML — Network-first
        if (request.headers.get('accept')?.includes('text/html')) {
            event.respondWith(networkFirst(request, RUNTIME_CACHE));
            return;
        }

        // CSS·JS·이미지·SVG — Stale-while-revalidate
        if (
            request.destination === 'style' ||
            request.destination === 'script' ||
            request.destination === 'image' ||
            url.pathname.endsWith('.css') ||
            url.pathname.endsWith('.js') ||
            url.pathname.endsWith('.svg')
        ) {
            event.respondWith(staleWhileRevalidate(request, STATIC_CACHE));
            return;
        }
    }
    // 그 외는 기본 처리
});

/* ─────────────── 전략 함수 ─────────────── */

async function cacheFirst(request, cacheName) {
    const cached = await caches.match(request);
    if (cached) return cached;
    try {
        const response = await fetch(request);
        if (response.ok) {
            const cache = await caches.open(cacheName);
            cache.put(request, response.clone());
        }
        return response;
    } catch (err) {
        return new Response('', { status: 503, statusText: 'Offline' });
    }
}

async function networkFirst(request, cacheName) {
    try {
        const response = await fetch(request);
        if (response.ok) {
            const cache = await caches.open(cacheName);
            cache.put(request, response.clone());
        }
        return response;
    } catch (err) {
        const cached = await caches.match(request);
        if (cached) return cached;
        // HTML 폴백 — 오프라인이면 / 응답
        const offline = await caches.match('/');
        if (offline) return offline;
        return new Response('Offline', { status: 503 });
    }
}

async function staleWhileRevalidate(request, cacheName) {
    const cached = await caches.match(request);
    const networkPromise = fetch(request)
        .then((response) => {
            if (response.ok) {
                caches.open(cacheName).then((cache) => cache.put(request, response.clone()));
            }
            return response;
        })
        .catch(() => null);

    return cached || networkPromise || new Response('', { status: 503 });
}

/* ─────────────── 메시지 처리 (manual update) ─────────────── */
self.addEventListener('message', (event) => {
    if (event.data?.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
});
