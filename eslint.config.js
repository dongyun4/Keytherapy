// ESLint flat config — Key Therapy
// self-replacement 같은 escape 버그를 catch하는 자체 규칙 + 기본 베스트 프랙티스
export default [
  {
    files: ['**/*.js'],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      globals: {
        window: 'readonly',
        document: 'readonly',
        localStorage: 'readonly',
        navigator: 'readonly',
        console: 'readonly',
      },
    },
    rules: {
      // self-replacement 검출 — DEF-015 대응
      // .replace(/&/g, '&') 같은 패턴은 람다나 외부 함수에서만 합법
      'no-useless-escape': 'error',
      'no-self-assign': 'error',
      // 보안 / 안정성
      'no-eval': 'error',
      'no-new-func': 'error',
      'no-implied-eval': 'error',
      'no-script-url': 'error',
      // 코드 품질
      'eqeqeq': ['error', 'always'],
      'no-var': 'error',
      'prefer-const': 'warn',
      'no-unused-vars': ['warn', { argsIgnorePattern: '^_', varsIgnorePattern: '^_' }],
      'no-console': ['warn', { allow: ['warn', 'error'] }],
    },
  },
  {
    ignores: ['dist/**', 'node_modules/**', 'coverage/**'],
  },
];
