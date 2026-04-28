// Vite 설정 — Key Therapy
// 단일 페이지 정적 사이트(SSG 미사용). 점진적 모듈 분리를 위해 root는 그대로.
import { defineConfig } from 'vite';

export default defineConfig({
  // 프로젝트 루트 — index.html 위치
  root: '.',

  // 정적 자산 디렉토리 — manifest.json, og-cover.svg, favicon 등
  publicDir: 'public',

  // 개발 서버
  server: {
    port: 5173,
    open: true,           // 자동 브라우저 오픈
    host: '127.0.0.1',    // 로컬만 (외부 노출 금지)
    strictPort: false,    // 포트 사용 중이면 자동 다음 포트
    cors: true,
  },

  // 프리뷰 서버 (npm run preview)
  preview: {
    port: 4173,
    host: '127.0.0.1',
    strictPort: false,
  },

  // 빌드 설정
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    sourcemap: false,         // 운영 — 소스맵 비공개. 디버깅 필요 시 'hidden'으로
    minify: 'esbuild',        // esbuild minify가 가장 빠름
    cssMinify: 'esbuild',
    target: 'es2020',         // 모던 브라우저 (iOS 14+, Safari 14+)
    chunkSizeWarningLimit: 1500,  // 단일 파일 시점에는 크게. 모듈 분리 후 줄일 것
    rollupOptions: {
      output: {
        // 캐시 무효화를 위한 hash 포함 파일명
        entryFileNames: 'assets/[name]-[hash].js',
        chunkFileNames: 'assets/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash].[ext]',
      },
    },
    // CSS 코드 분할 — 모듈별 별도 CSS 파일 생성 (S5 모듈 분리 시 활용)
    cssCodeSplit: true,
    // brotli 사이즈 리포트 — 빌드 후 npm run build 결과에 표시
    reportCompressedSize: true,
  },

  // CSS 처리
  css: {
    devSourcemap: true,      // 개발 시 CSS 소스맵 활성
    transformer: 'postcss',  // PostCSS — 향후 autoprefixer 등 추가 가능
  },

  // 테스트 (vitest)
  test: {
    environment: 'happy-dom',
    globals: true,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
      exclude: ['vite-starter/', 'dist/', 'node_modules/', 'tests/fixtures/'],
    },
  },

  // 의존성 사전 번들링 (모듈 분리 후 라이브러리 추가 시점)
  optimizeDeps: {
    include: [],
  },
});
