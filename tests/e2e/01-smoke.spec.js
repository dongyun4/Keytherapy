/**
 * Smoke 테스트 — 기본 페이지 로드 + 핵심 element 존재 확인
 */
import { test, expect } from '@playwright/test';

test.describe('Smoke', () => {
    test('1. 페이지 로드 + Hero 표시', async ({ page }) => {
        await page.goto('/');
        await expect(page).toHaveTitle(/Key Therapy/);
        await expect(page.locator('.kt-hero__title, .hero-title')).toContainText('Key Therapy');
    });

    test('2. 모드 5버튼 (단문/장문/글쓰기/ASMR/게임) 모두 존재', async ({ page }) => {
        await page.goto('/');
        const labels = ['단문 연습', '장문 연습', '글쓰기', 'ASMR 모드', '게임하기'];
        for (const label of labels) {
            await expect(page.getByRole('button', { name: new RegExp(label) })).toBeVisible();
        }
    });

    test('3. 통계 4값 (속도/정확도/평균/최고) 존재', async ({ page }) => {
        await page.goto('/');
        await expect(page.locator('#speedStat, [data-stat="speed"]')).toBeVisible();
        await expect(page.locator('#accuracyStat, [data-stat="accuracy"]')).toBeVisible();
    });

    test('4. CSS·JS 모두 200 응답', async ({ page }) => {
        const failed = [];
        page.on('response', (resp) => {
            if (!resp.ok() && !resp.url().includes('/_vercel/')) {
                failed.push(`${resp.status()} ${resp.url()}`);
            }
        });
        await page.goto('/');
        await page.waitForLoadState('networkidle');
        expect(failed, `Failed resources:\n${failed.join('\n')}`).toHaveLength(0);
    });

    test('5. Console 에러 없음 (분석 스크립트 404 제외)', async ({ page }) => {
        const errors = [];
        page.on('pageerror', (err) => errors.push(err.message));
        page.on('console', (msg) => {
            if (msg.type() === 'error' && !msg.text().includes('_vercel')) {
                errors.push(msg.text());
            }
        });
        await page.goto('/');
        await page.waitForLoadState('networkidle');
        expect(errors).toHaveLength(0);
    });
});
