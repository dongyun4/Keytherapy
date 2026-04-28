/**
 * 모바일 전용 — 한 줄 fit·overscroll·키보드
 */
import { test, expect } from '@playwright/test';

test.describe('Mobile', () => {
    test.use({ viewport: { width: 375, height: 812 } });  // iPhone 14 Pro 크기

    test('22. 모바일 — Hero 부제 (N° 01·EDITION) 480px 미만에서 숨김', async ({ page }) => {
        await page.setViewportSize({ width: 360, height: 800 });
        await page.goto('/');
        // CSS @media에 의해 hidden — display: none 또는 매우 작게
        const beforeDisplay = await page.locator('.kt-hero, .hero-section').evaluate((el) =>
            getComputedStyle(el, '::before').display
        );
        // 480px 미만에서는 ::before/::after가 none
        expect(['none', '']).toContain(beforeDisplay);
    });

    test('23. 모바일 — 단문 예문 한 줄 fit (autofit JS)', async ({ page }) => {
        await page.goto('/');
        await page.getByRole('button', { name: /단문 연습/ }).click();
        const line = page.locator('#current-typing-line');
        const overflowX = await line.evaluate((el) => getComputedStyle(el).overflowX);
        expect(['hidden', 'clip']).toContain(overflowX);
    });

    test('24. 모바일 — overscroll-behavior contain', async ({ page }) => {
        await page.goto('/');
        const html = await page.locator('html').evaluate((el) =>
            getComputedStyle(el).overscrollBehavior
        );
        expect(html).toContain('contain');
    });

    test('25. 모바일 — input 폰트 ≥ 16px (iOS 줌 회피)', async ({ page }) => {
        await page.goto('/');
        const input = page.locator('#typing-input-field');
        const fontSize = await input.evaluate((el) =>
            parseInt(getComputedStyle(el).fontSize, 10)
        );
        expect(fontSize).toBeGreaterThanOrEqual(16);
    });

    test('26. 모바일 — 터치 타깃 44px (모드 버튼)', async ({ page }) => {
        await page.goto('/');
        const btn = page.locator('button[data-practice-type="short"]');
        const box = await btn.boundingBox();
        expect(box.height).toBeGreaterThanOrEqual(40);  // 44 - 4px tolerance
    });
});
