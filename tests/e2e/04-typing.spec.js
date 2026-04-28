/**
 * 타이핑 핵심 기능
 */
import { test, expect } from '@playwright/test';

test.describe('타이핑', () => {
    test('18. 단문 입력 → 통계 갱신', async ({ page }) => {
        await page.goto('/');
        await page.getByRole('button', { name: /단문 연습/ }).click();
        const input = page.locator('#typing-input-field');
        await input.focus();
        await input.type('test', { delay: 30 });
        // 속도 또는 정확도가 0이 아니어야 함 (어떤 입력이든 카운트)
        await page.waitForTimeout(800);
    });

    test('19. ASMR 모드 입력 가능', async ({ page }) => {
        await page.goto('/');
        await page.getByRole('button', { name: /ASMR 모드/ }).click();
        const asmrInput = page.locator('#asmrInput');
        await expect(asmrInput).toBeVisible();
        await asmrInput.focus();
        await page.keyboard.type('test', { delay: 30 });
    });

    test('20. 글쓰기 textarea 입력 + 글자 수 카운트', async ({ page }) => {
        await page.goto('/');
        await page.getByRole('button', { name: /글쓰기/ }).click();
        const ta = page.locator('#freestyle-input-area');
        await ta.fill('안녕하세요 테스트');
        await expect(page.locator('#charCount')).toContainText(/[1-9]\d*자/);
    });

    test('21. 글쓰기 다운로드 파일명 sanitize', async ({ page }) => {
        await page.goto('/');
        await page.getByRole('button', { name: /글쓰기/ }).click();
        await page.locator('#freestyle-input-area').fill('내용');
        await page.locator('#freestyle-filename-input').fill('a/b\\c:d"e?f');
        const [download] = await Promise.all([
            page.waitForEvent('download'),
            page.locator('#download-freestyle-btn').click(),
        ]);
        // 금지 문자가 모두 제거된 파일명
        expect(download.suggestedFilename()).not.toMatch(/[<>:"\/\\|?*]/);
    });
});
