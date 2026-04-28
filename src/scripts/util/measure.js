/**
 * Key Therapy — 텍스트 측정 유틸
 * ========================================================
 * 인라인 JS 의 fitMobileTypingLine / fitAsmrLine 을 ESM 모듈화.
 * Canvas 2D measureText 기반 — DOM 변형 없는 측정으로 layout thrash 0.
 *
 * 사용 예:
 *   import { measureTextWidth, fitToWidth } from '../util/measure.js';
 *
 *   const width = measureTextWidth('안녕하세요', 18, 'serif', '0.02em');
 *
 *   const targetSize = fitToWidth({
 *     text: '안녕하세요',
 *     containerWidth: 300,
 *     refSize: 18,
 *     min: 11,
 *     max: 18,
 *     fontFamily: 'serif',
 *     letterSpacing: '0.02em',
 *   });
 */

// 단일 canvas context — 페이지 전체에서 공유 (메모리 효율)
let _ctx = null;
function getCtx() {
    if (!_ctx) {
        try { _ctx = document.createElement('canvas').getContext('2d'); }
        catch (_) { return null; }
    }
    return _ctx;
}

// LRU 캐시 — 같은 (text, fontSize, fontFamily, letterSpacing) 조합은 재측정 안 함
const _cache = new Map();
const MAX_CACHE = 200;

/**
 * 텍스트 자연 너비 측정
 * @param {string} text
 * @param {number} fontSize - px 단위
 * @param {string} fontFamily
 * @param {string} [letterSpacing='normal']
 * @returns {number} - 픽셀 단위 너비
 */
export function measureTextWidth(text, fontSize, fontFamily, letterSpacing = 'normal') {
    if (!text) return 0;
    const ctx = getCtx();
    if (!ctx) return text.length * fontSize; // 폴백
    const cacheKey = `${text}|${fontSize}|${fontFamily}|${letterSpacing}`;
    if (_cache.has(cacheKey)) return _cache.get(cacheKey);

    ctx.font = `${fontSize}px ${fontFamily}`;
    let width = ctx.measureText(text).width;
    // canvas measureText는 letter-spacing을 반영하지 않음 → 수동 가산
    if (letterSpacing && letterSpacing !== 'normal') {
        const ls = parseFloat(letterSpacing) || 0;
        if (ls) width += ls * Math.max(0, text.length - 1);
    }

    _cache.set(cacheKey, width);
    if (_cache.size > MAX_CACHE) {
        const first = _cache.keys().next().value;
        _cache.delete(first);
    }
    return width;
}

/**
 * 컨테이너에 맞는 폰트 크기 계산
 * @param {Object} opts
 * @param {string} opts.text
 * @param {number} opts.containerWidth - 가용 폭 (padding 차감 후)
 * @param {number} opts.refSize - 측정 기준 폰트 크기 (px)
 * @param {number} [opts.min=11] - 최소 폰트 크기 (px)
 * @param {number} [opts.max] - 최대 폰트 크기 (px). 기본은 refSize
 * @param {string} [opts.fontFamily='serif']
 * @param {string} [opts.letterSpacing='normal']
 * @returns {number} - 적용할 폰트 크기 (px)
 */
export function fitToWidth(opts) {
    const {
        text,
        containerWidth,
        refSize,
        min = 11,
        max = refSize,
        fontFamily = 'serif',
        letterSpacing = 'normal',
    } = opts;
    if (!text || containerWidth <= 0) return refSize;

    const naturalWidth = measureTextWidth(text, refSize, fontFamily, letterSpacing);
    if (naturalWidth <= containerWidth) {
        return Math.min(refSize, max);
    }
    // 비율 계산 후 floor + min/max clamp
    const target = Math.floor(refSize * (containerWidth / naturalWidth));
    return Math.max(min, Math.min(target, max));
}

/**
 * 캐시 초기화 (테스트·메모리 압박 시)
 */
export function clearMeasureCache() {
    _cache.clear();
}

/**
 * 캐시 통계 (디버깅)
 */
export function getMeasureCacheStats() {
    return { size: _cache.size, max: MAX_CACHE };
}
