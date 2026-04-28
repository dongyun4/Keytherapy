/**
 * Key Therapy — Playwright config
 * ========================================================
 * 30 시나리오 e2e + visual diff. 데스크톱·모바일·테마 매트릭스.
 */
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
    testDir: './tests/e2e',
    fullyParallel: true,
    forbidOnly: !!process.env.CI,
    retries: process.env.CI ? 2 : 0,
    workers: process.env.CI ? 2 : undefined,
    reporter: process.env.CI ? [['github'], ['html']] : 'html',

    use: {
        baseURL: 'http://localhost:4173',  // vite preview
        trace: 'retain-on-failure',
        screenshot: 'only-on-failure',
        video: 'retain-on-failure',
        // 한국어 사이트 — locale 명시
        locale: 'ko-KR',
        timezoneId: 'Asia/Seoul',
    },

    /* 디바이스 매트릭스 */
    projects: [
        {
            name: 'desktop-chromium',
            use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } },
        },
        {
            name: 'desktop-firefox',
            use: { ...devices['Desktop Firefox'], viewport: { width: 1440, height: 900 } },
        },
        {
            name: 'desktop-webkit',
            use: { ...devices['Desktop Safari'], viewport: { width: 1440, height: 900 } },
        },
        {
            name: 'tablet',
            use: { ...devices['iPad Mini'] },
        },
        {
            name: 'mobile-iphone',
            use: { ...devices['iPhone 14 Pro'] },
        },
        {
            name: 'mobile-android',
            use: { ...devices['Pixel 7'] },
        },
    ],

    /* 자체 dev server 자동 실행 */
    webServer: {
        command: 'npm run preview',
        url: 'http://localhost:4173',
        reuseExistingServer: !process.env.CI,
        timeout: 60_000,
    },

    /* Visual diff 임계치 */
    expect: {
        toHaveScreenshot: { maxDiffPixelRatio: 0.02 },  // 2% 이내 차이는 통과
    },
});
