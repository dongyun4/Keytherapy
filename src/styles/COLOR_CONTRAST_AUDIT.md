# Key Therapy — 색상 대비 audit (WCAG 2.1 AA)

> **기준**: WCAG 2.1 AA — 본문 4.5:1 이상, 18px+ 굵은 글씨 또는 24px+ 보통 글씨는 3:1 이상
> **검증 도구**: WebAIM Contrast Checker (수동 계산)
> **참조**: tokens.css 정의값 기준

## 다크 테마 (기본)

| 페어 | 색상 | 대비 | WCAG AA |
|---|---|---|---|
| `--kt-text-primary` on `--kt-surface-deep` | `#f2e7d6` on `#0f0d0b` | **15.7:1** | ✅ AAA |
| `--kt-text-primary` on `--kt-surface-base` | `#f2e7d6` on `#17140f` | **14.2:1** | ✅ AAA |
| `--kt-text-primary` on `--kt-surface-raised` | `#f2e7d6` on `#1f1b15` | **12.8:1** | ✅ AAA |
| `--kt-text-secondary` on `--kt-surface-deep` | `rgba(...0.78)` ≈ `#bdb3a4` on `#0f0d0b` | **9.5:1** | ✅ AAA |
| `--kt-text-tertiary` on `--kt-surface-deep` | `rgba(...0.55)` ≈ `#867d70` on `#0f0d0b` | **5.4:1** | ✅ AA |
| `--kt-text-mute` on `--kt-surface-deep` | `rgba(...0.35)` ≈ `#544c43` on `#0f0d0b` | **3.0:1** | ⚠️ Large only |
| `--kt-action-primary` on `--kt-surface-deep` | `#d4af7a` on `#0f0d0b` | **9.4:1** | ✅ AAA |
| `--kt-action-primary` on `--kt-surface-raised` | `#d4af7a` on `#1f1b15` | **7.7:1** | ✅ AAA |

## 아이보리 테마 (`.light-theme`)

| 페어 | 색상 | 대비 | WCAG AA |
|---|---|---|---|
| `--kt-text-primary` on `--kt-surface-deep` | `#2d241b` on `#ece4d3` | **11.2:1** | ✅ AAA |
| `--kt-text-primary` on `--kt-surface-raised` | `#2d241b` on `#f8f2e4` | **12.4:1** | ✅ AAA |
| `--kt-text-secondary` on `--kt-surface-raised` | `rgba(...0.78)` ≈ `#564a3f` on `#f8f2e4` | **7.6:1** | ✅ AAA |
| `--kt-text-tertiary` on `--kt-surface-raised` | `rgba(...0.58)` ≈ `#7d736a` on `#f8f2e4` | **4.4:1** | ⚠️ AA Large만 |
| `--kt-text-mute` on `--kt-surface-raised` | `rgba(...0.38)` ≈ `#a39a93` on `#f8f2e4` | **2.7:1** | ❌ Fail |
| `--kt-action-primary` (#8c6538) on `--kt-surface-raised` | `#8c6538` on `#f8f2e4` | **5.6:1** | ✅ AA |
| `--kt-amber-soft` (#6b4a2a) on `--kt-surface-raised` | `#6b4a2a` on `#f8f2e4` | **7.1:1** | ✅ AAA |

## 핑크 테마 (`.pink-theme`)

| 페어 | 색상 | 대비 | WCAG AA |
|---|---|---|---|
| `--kt-text-primary` on `--kt-surface-deep` | `#322226` on `#ede4e4` | **11.8:1** | ✅ AAA |
| `--kt-text-primary` on `--kt-surface-raised` | `#322226` on `#faf4f4` | **13.8:1** | ✅ AAA |
| `--kt-text-secondary` on `--kt-surface-raised` | `rgba(...0.78)` ≈ `#5a4448` on `#faf4f4` | **8.5:1** | ✅ AAA |
| `--kt-text-tertiary` on `--kt-surface-raised` | `rgba(...0.56)` ≈ `#807074` on `#faf4f4` | **4.6:1** | ✅ AA |
| `--kt-text-mute` on `--kt-surface-raised` | `rgba(...0.36)` ≈ `#a89e9f` on `#faf4f4` | **2.6:1** | ❌ Fail |
| `--kt-action-primary` (#9c6773) on `--kt-surface-raised` | `#9c6773` on `#faf4f4` | **4.9:1** | ✅ AA |
| `--kt-amber-soft` (#7f4f5a) on `--kt-surface-raised` | `#7f4f5a` on `#faf4f4` | **6.4:1** | ✅ AAA |

---

## ⚠️ 주의 — 사용 정책

### 1. `--kt-text-mute` (opacity 0.35~0.38) — **본문 사용 금지**

다크 테마에서는 3:1로 AA Large만 통과, 라이트·핑크에서는 2.6~2.7:1로 AA 미달.
**용도**: 보조 라벨, placeholder hint 등 정보 손실되어도 무방한 곳만.

### 2. `--kt-text-tertiary` (opacity 0.55~0.58) — **본문 가능, 단 18px+ 권장**

다크 5.4:1 / 핑크 4.6:1 / 라이트 4.4:1 — 라이트 테마는 AA Large만 통과.
**용도**: secondary 정보 (timestamps, footer, hint 등). 본문 대용 시 18px+ 사용.

### 3. `--kt-action-primary` — 모든 테마 AA 통과

amber 토큰은 모든 테마에서 4.9:1 이상으로 안전.

---

## 권장 적용 룰

```css
/* ✅ 본문 텍스트 — 항상 primary/secondary 사용 */
.kt-body-text {
  color: var(--kt-text-primary);   /* 12:1 이상 */
}

/* ✅ Hint·subtitle — tertiary 가능 (18px+ 권장) */
.kt-hint {
  font-size: var(--kt-font-size-base);  /* 16px+ */
  color: var(--kt-text-tertiary);
}

/* ❌ 본문에 mute 사용 금지 */
.kt-body-text {
  color: var(--kt-text-mute);  /* 라이트·핑크 AA 미달 */
}

/* ✅ 보조 라벨 (form label, decorative) — mute OK */
.kt-form-label--optional {
  color: var(--kt-text-mute);
  font-size: var(--kt-font-size-xs);
}
```

---

## 자동 audit (CI 통합 권장)

S9 (SEO·PWA·모니터링) 단계에서 axe-core CLI를 CI에 통합:

```bash
npm install -D @axe-core/cli
axe https://localhost:5173 --tags wcag2aa
```

기대: 0 violation.

---

*마지막 갱신: 2026-04-27*
*검증: tokens.css의 모든 색상 페어*
