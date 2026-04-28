/**
 * 테마 전환 + 앰비언스 효과
 */
import { test, expect } from '@playwright/test';

test.describe('테마 & 앰비언스', () => {
    test('12. 다크 → 아이보리 테마 전환', async ({ page }) => {
        await page.goto('/');
        await page.locator('#themeSelect').selectOption('light');
        await expect(page.locator('body')).toHaveClass(/light-theme/);
    });

    test('13. 다크 → 핑크 테마 전환', async ({ page }) => {
        await page.goto('/');
        await page.locator('#themeSelect').selectOption('pink');
        await expect(page.locator('body')).toHaveClass(/pink-theme/);
    });

    test('14. 새로고침 후 테마 유지 (localStorage)', async ({ page }) => {
        await page.goto('/');
        await page.locator('#themeSelect').selectOption('pink');
        await page.reload();
        await expect(page.locator('body')).toHaveClass(/pink-theme/);
    });

    test('15. 앰비언스 효과 4종 다크 (은은·촛불·설야·반딧불)', async ({ page }) => {
        await page.goto('/');
        const buttons = page.locator('.ambience-picker button[data-theme-scope="dark"]');
        await expect(buttons).toHaveCount(4);
        for (let i = 0; i < 4; i++) {
            await buttons.nth(i).click();
            await page.waitForTimeout(300);
        }
    });

    test('16. 앰비언스 — 핑크 테마에서 핑크 전용 4종 표시', async ({ page }) => {
        await page.goto('/');
        await page.locator('#themeSelect').selectOption('pink');
        const buttons = page.locator('.ambience-picker button[data-theme-scope="pink"]:visible');
        await expect(buttons).toHaveCount(4);
    });

    test('17. 컬러 토큰 적용 — light theme 본문 색상 검증', async ({ page }) => {
        await page.goto('/');
        await page.locator('#themeSelect').selectOption('light');
        const color = await page.locator('body').evaluate((el) =>
            getComputedStyle(el).color
        );
        // 라이트 테마 ink는 #2d241b 근처
        expect(color).toMatch(/rgb\(45,?\s*36,?\s*27\)/);
    });
});
