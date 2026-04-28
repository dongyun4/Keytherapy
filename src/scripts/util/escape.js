/**
 * Key Therapy — HTML escape 유틸 (XSS 방지)
 * ========================================================
 * S1 작업의 escapeHtml 정상화 + DEF-015 회귀 방지를 위한 단위 모듈.
 * Vitest 단위 테스트(`escape.spec.js`) 와 짝.
 *
 * ⚠️ 본 함수의 self-replacement 패턴(`replace(/&/g, '&')`)은
 * ESLint 룰(`no-useless-escape`, `no-self-assign`)이 검출.
 */

/**
 * HTML entity escape — 5종 (& < > " ')
 * @param {*} input - 어떤 타입이든. 자동으로 String 변환
 * @returns {string}
 */
export function escapeHtml(input) {
    return String(input)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

/**
 * 파일명 sanitize — Win/Mac/Linux 금지 문자 + 컨트롤 문자 + 예약명 회피
 * @param {string} raw
 * @returns {string}
 */
export function sanitizeFilename(raw) {
    if (!raw) return '';
    let s = String(raw)
        .replace(/[<>:"/\\|?*]/g, '')           // Windows 금지 문자
        .replace(/[\x00-\x1f\x7f]/g, '')         // 컨트롤 문자
        .replace(/^[.\s]+|[.\s]+$/g, '');        // 앞뒤 공백·마침표
    // Windows 예약 이름 (CON, PRN, AUX, NUL, COM1~9, LPT1~9)
    if (/^(con|prn|aux|nul|com[1-9]|lpt[1-9])(\..*)?$/i.test(s)) {
        s = '_' + s;
    }
    if (s.length > 200) s = s.slice(0, 200);
    return s;
}

/**
 * 안전한 문자열 비교 (timing attack 방어 — 길이 비교는 무시)
 * 본 사이트는 인증 등이 없어 직접적인 timing attack 위험은 없으나,
 * 향후 토큰 비교 시 사용 가능.
 */
export function safeCompare(a, b) {
    a = String(a); b = String(b);
    if (a.length !== b.length) return false;
    let mismatch = 0;
    for (let i = 0; i < a.length; i++) mismatch |= a.charCodeAt(i) ^ b.charCodeAt(i);
    return mismatch === 0;
}
