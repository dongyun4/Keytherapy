/**
 * escape.js 단위 테스트
 * ========================================================
 * DEF-015 — 1년간 발견되지 않았던 self-replacement 버그 재발 방지.
 * Vitest 또는 Jest 호환.
 *
 * 실행:
 *   npm run test       # watch mode
 *   npm run test:run   # CI mode (1회)
 */

import { describe, it, expect } from 'vitest';
import { escapeHtml, sanitizeFilename, safeCompare } from '../src/scripts/util/escape.js';

describe('escapeHtml', () => {
    it('escapes & to &amp;', () => {
        expect(escapeHtml('AT&T')).toBe('AT&amp;T');
    });

    it('escapes < and > for tag context', () => {
        expect(escapeHtml('<script>alert(1)<\/script>')).toBe('&lt;script&gt;alert(1)&lt;\/script&gt;');
    });

    it('escapes " for attribute context', () => {
        expect(escapeHtml('say "hi"')).toBe('say &quot;hi&quot;');
    });

    it("escapes ' for attribute context", () => {
        expect(escapeHtml("it's me")).toBe('it&#39;s me');
    });

    it('handles empty string', () => {
        expect(escapeHtml('')).toBe('');
    });

    it('handles non-string input', () => {
        expect(escapeHtml(null)).toBe('null');
        expect(escapeHtml(undefined)).toBe('undefined');
        expect(escapeHtml(42)).toBe('42');
        expect(escapeHtml(true)).toBe('true');
    });

    /**
     * ⚠️ Self-replacement 버그 회귀 검출 (DEF-015 핵심)
     * 만약 누군가 실수로 .replace(/&/g, '&') (entity 변환 안 됨) 으로 되돌리면
     * 결과 길이가 입력과 같거나 작아지고, 이 테스트가 실패함.
     */
    it('does not self-replace — & must become longer (&amp;)', () => {
        const out = escapeHtml('&');
        expect(out.length).toBeGreaterThan(1);
        expect(out).toBe('&amp;');
    });

    it('does not self-replace — < must become longer (&lt;)', () => {
        expect(escapeHtml('<').length).toBeGreaterThan(1);
        expect(escapeHtml('<')).toBe('&lt;');
    });

    it('multiple entities in one string', () => {
        expect(escapeHtml('A&B<C>D"E\'F'))
            .toBe('A&amp;B&lt;C&gt;D&quot;E&#39;F');
    });

    it('Korean text passes through (no escape)', () => {
        expect(escapeHtml('안녕하세요')).toBe('안녕하세요');
    });

    it('preserves emoji', () => {
        expect(escapeHtml('🎧 Hello')).toBe('🎧 Hello');
    });
});

describe('sanitizeFilename', () => {
    it('removes Windows forbidden chars', () => {
        expect(sanitizeFilename('a<b>c:d"e/f\\g|h?i*j')).toBe('abcdefghij');
    });

    it('removes control characters', () => {
        expect(sanitizeFilename('a\x00b\x1fc\x7fd')).toBe('abcd');
    });

    it('trims leading/trailing dots and spaces', () => {
        expect(sanitizeFilename('  ...hello...  ')).toBe('hello');
    });

    it('escapes Windows reserved names', () => {
        expect(sanitizeFilename('CON')).toBe('_CON');
        expect(sanitizeFilename('com1')).toBe('_com1');
        expect(sanitizeFilename('LPT9.txt')).toBe('_LPT9.txt');
    });

    it('preserves Korean filename', () => {
        expect(sanitizeFilename('내일기장')).toBe('내일기장');
    });

    it('limits to 200 chars', () => {
        const long = 'a'.repeat(300);
        expect(sanitizeFilename(long).length).toBe(200);
    });

    it('handles empty/null input', () => {
        expect(sanitizeFilename('')).toBe('');
        expect(sanitizeFilename(null)).toBe('');
        expect(sanitizeFilename(undefined)).toBe('');
    });
});

describe('safeCompare', () => {
    it('returns true for identical strings', () => {
        expect(safeCompare('abc', 'abc')).toBe(true);
    });

    it('returns false for different strings', () => {
        expect(safeCompare('abc', 'abd')).toBe(false);
    });

    it('returns false for different lengths', () => {
        expect(safeCompare('abc', 'abcd')).toBe(false);
    });

    it('handles empty strings', () => {
        expect(safeCompare('', '')).toBe(true);
        expect(safeCompare('', 'a')).toBe(false);
    });
});
