/**
 * 접근성 (WCAG 2.1 AA)
 */
import { test, expect } from '@playwright/test';

test.describe('Accessibility', () => {
    test('27. Skip link Tab 1회 — 표시', async ({ page }) => {
        await page.goto('/');
        await page.keyboard.press('Tab');
        const skipLink = page.locator('.kt-skip-link, [class*="skip-link"]').first();
        await expect(skipLink).toBeFocused();
    });

    test('28. 키보드만으로 모드 전환 (Tab + Enter)', async ({ page }) => {
        await page.goto('/');
        // Tab 여러 번 해서 단문 버튼 도달
        for (let i = 0; i < 10; i++) {
            await page.keyboard.press('Tab');
            const focused = await page.evaluate(() => document.activeElement?.dataset?.practiceType);
            if (focused === 'short') break;
        }
        await page.keyboard.press('Enter');
        await expect(page.locator('#current-typing-line, .kt-typing__line--current')).toBeVisible();
    });

    test('29. ASMR 모달 Esc로 닫힘 (focus trap)', async ({ page }) => {
        await page.goto('/');
        await page.getByRole('button', { name: /ASMR 모드/ }).click();
        await expect(page.locator('#asmr-overlay')).toHaveClass(/visible/);
        await page.keyboard.press('Escape');
        await expect(page.locator('#asmr-overlay')).not.toHaveClass(/visible/);
    });

    test('30. focus-visible outline 적용 (다크 테마 amber)', async ({ page }) => {
        await page.goto('/');
        await page.locator('button[data-practice-type="short"]').focus();
        const outline = await page.locator('button[data-practice-type="short"]').evaluate((el) =>
            getComputedStyle(el).outlineWidth
        );
        // outline이 있어야 함 (0px 아님)
        expect(parseInt(outline, 10)).toBeGreaterThanOrEqual(2);
    });
});
