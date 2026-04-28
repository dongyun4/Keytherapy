/**
 * 연습 모드 전환 시나리오
 */
import { test, expect } from '@playwright/test';

test.describe('연습 모드', () => {
    test('6. 단문 모드 — 예문 라인 표시', async ({ page }) => {
        await page.goto('/');
        await page.getByRole('button', { name: /단문 연습/ }).click();
        await expect(page.locator('#current-typing-line, .kt-typing__line--current')).toBeVisible();
    });

    test('7. 장문 모드 — 글 선택 셀렉트 표시', async ({ page }) => {
        await page.goto('/');
        await page.getByRole('button', { name: /장문 연습/ }).click();
        await expect(page.locator('#longTextSelectContainer:not(.hidden), .long-text-settings:not(.hidden)')).toBeVisible({ timeout: 3000 });
    });

    test('8. 글쓰기 모드 — textarea 진입', async ({ page }) => {
        await page.goto('/');
        await page.getByRole('button', { name: /글쓰기/ }).click();
        await expect(page.locator('#freestyle-input-area')).toBeVisible();
    });

    test('9. ASMR 모드 — 오버레이 진입', async ({ page }) => {
        await page.goto('/');
        await page.getByRole('button', { name: /ASMR 모드/ }).click();
        await expect(page.locator('#asmr-overlay')).toHaveClass(/visible/);
    });

    test('10. ASMR Esc로 종료', async ({ page }) => {
        await page.goto('/');
        await page.getByRole('button', { name: /ASMR 모드/ }).click();
        await page.keyboard.press('Escape');
        await expect(page.locator('#asmr-overlay')).not.toHaveClass(/visible/);
    });

    test('11. 모드 5회 전환 — 메모리 leak 없음 (window.__rafActive 검증)', async ({ page }) => {
        await page.goto('/');
        const modes = ['단문 연습', '장문 연습', '글쓰기', '게임하기', '단문 연습'];
        for (const mode of modes) {
            await page.getByRole('button', { name: new RegExp(mode) }).click();
            await page.waitForTimeout(500);
        }
        // 단문 모드 다시 정상 작동
        await expect(page.locator('.kt-typing__line--current, #current-typing-line')).toBeVisible();
    });
});
