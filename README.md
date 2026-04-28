# Key Therapy — Vite Starter Files

이 폴더의 파일들은 사용자 로컬 환경에서 **Vite 빌드 인프라를 시작할 때 사용할 설정 파일**입니다. Cowork 세션은 정적 파일 편집만 가능하므로, 실제 빌드 실행은 사용자 Mac/PC에서 진행해야 합니다.

## 파일 목록

| 파일 | 용도 |
|---|---|
| `package.json` | 프로젝트 메타데이터 + 의존성 + 스크립트 |
| `vite.config.js` | Vite 빌드 설정 (개발 서버, 빌드 옵션, 테스트) |
| `.gitignore` | git 제외 패턴 |
| `.nvmrc` | Node 20 LTS 고정 |
| `.prettierrc.json` | 코드 포매터 설정 |
| `eslint.config.js` | 린터 설정 (escape 버그 검출 포함) |

## 사용 방법

자세한 단계별 가이드는 `KEYTHERAPY_VITE_SETUP_GUIDE.md` 참조.

요약:
1. 위 파일들을 프로젝트 루트로 복사
2. `nvm use` (Node 20 자동 설정)
3. `npm install`
4. `npm run dev`
