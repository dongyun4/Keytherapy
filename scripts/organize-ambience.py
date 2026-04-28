"""
sound effect/ 의 49개 파일을 제목 기반으로 카테고리 분류 + 깔끔한 이름 + manifest 생성.
"""
import os
import shutil
import json
from pathlib import Path


SRC = Path('sound effect')
DST = Path('public/ambience')

# 카테고리 매핑 — 파일명 패턴 → (카테고리, 표시 이름, 이모지)
def categorize(filename):
    f = filename.lower()
    # 우선순위 상위부터 매치
    if 'thunder' in f or 'thunderstorm' in f:
        return ('thunder', '천둥')
    if 'underwater' in f:
        return ('special', '수중')
    if 'wind-chime' in f or 'wind_chime' in f:
        return ('special', '풍경(風磬)')
    if 'cafe' in f or 'diner' in f or 'restaurant' in f:
        return ('cafe', '카페·식당')
    if 'fireplace' in f or 'fire-' in f or 'fire_' in f or 'fire-with' in f or 'crackling' in f:
        return ('fire', '벽난로')
    if 'stream' in f or 'tumbling' in f:
        return ('stream', '시냇물')
    if 'ocean' in f or 'waves' in f or 'beach' in f or 'sandy' in f or 'shore' in f:
        return ('ocean', '바다')
    # forest before birds (more specific)
    if 'forest' in f and ('bird' in f or 'birds' in f):
        return ('forest', '숲·새소리')
    if 'forest' in f:
        return ('forest', '숲')
    if 'bird' in f and 'rain' in f:
        return ('rain', '비·새소리')  # 모닝 비+새 → rain 분류
    if 'rain' in f:
        return ('rain', '비')
    if 'wind' in f and 'storm' in f:
        return ('wind', '바람폭풍')
    if 'wind' in f:
        return ('wind', '바람')
    return ('etc', '기타')


def make_label(filename, cat_label):
    """파일명에서 의미 있는 keyword 추출해 한글 라벨 생성."""
    f = filename.lower()
    # 특수 라벨 매핑 (우선순위)
    keywords = [
        ('heavy-rain', '폭우 (창밖)'),
        ('gentle-rain', '부슬비'),
        ('relaxing-rain', '편안한 비'),
        ('calm-rain', '잔잔한 비'),
        ('light-rain', '가벼운 비'),
        ('long-loop', '롱 루프 비'),
        ('falling-rain', '떨어지는 비'),
        ('november-rain', '11월의 비'),
        ('morning-birds-and-rain', '비 오는 아침 새소리'),
        ('thunderstorm', '천둥번개'),
        ('thunder-sound', '먼 천둥'),
        ('thunder', '천둥'),
        ('nyc-diner', '뉴욕 다이너'),
        ('restaurant', '레스토랑'),
        ('windfarm-cafe', '카페 (풍력단지)'),
        ('fireplace-ambience', '벽난로 분위기'),
        ('fire-with-wet-wood', '젖은 장작 불'),
        ('nighttime-outdoor-fireplace', '밤의 야외 벽난로'),
        ('crackling-loop', '벽난로 크래클링'),
        ('the-fireplace', '벽난로'),
        ('forest-atmosphere', '숲 분위기'),
        ('birds-forest-river', '강가 숲 새소리'),
        ('birds-forest-spring', '봄 숲 새소리'),
        ('forest-soundscape-night', '밤의 숲'),
        ('forest-bird-harmonies', '새 합창'),
        ('forest-wind-with-crickets', '숲바람·귀뚜라미'),
        ('birds-forest-nature', '숲속 자연'),
        ('forestbirds-2', '숲의 새 ②'),
        ('forestbirds', '숲의 새'),
        ('peaceful-stream', '평화로운 시냇물'),
        ('stream-ambience', '시냇물 분위기'),
        ('calm-stream', '잔잔한 시내'),
        ('small-stream', '작은 시내'),
        ('tumbling-stream', '계곡물'),
        ('gentle-ocean', '부드러운 파도'),
        ('soft-ocean-waves', '잔잔한 파도'),
        ('water-ocean-waves', '바다 파도'),
        ('sandy-beach', '모래사장 파도'),
        ('relaxing-ocean', '편안한 바다'),
        ('ocean-beach-waves', '해변 파도'),
        ('waves-sfx', '파도'),
        ('indian-ocean', '인도양 일출'),
        ('cold-wind', '차가운 바람'),
        ('windstorm', '거센 바람'),
        ('soft-wind', '부드러운 바람'),
        ('wind-chime', '풍경'),
        ('underwater', '수중'),
    ]
    for k, label in keywords:
        if k in f:
            return label
    # fallback — 카테고리 라벨
    return cat_label


def main():
    if not SRC.exists():
        print(f"❌ {SRC} 없음")
        return
    DST.mkdir(parents=True, exist_ok=True)

    files = sorted([f for f in SRC.iterdir() if f.is_file() and f.suffix.lower() in ('.mp3', '.wav', '.ogg')])
    print(f"발견된 파일: {len(files)}개")

    # 중복 제거 (파일명에 '(1)' 포함된 것)
    seen_base = set()
    unique_files = []
    for f in files:
        base = f.name.replace(' (1)', '').replace(' (2)', '')
        if base in seen_base:
            print(f"  ⏭️  중복 스킵: {f.name}")
            continue
        seen_base.add(base)
        unique_files.append(f)

    # 카테고리별 분류
    by_cat = {}
    for f in unique_files:
        cat, cat_label = categorize(f.name)
        label = make_label(f.name, cat_label)
        by_cat.setdefault(cat, []).append((f, label, cat_label))

    # 복사 + manifest 생성
    manifest = {}
    for cat, items in sorted(by_cat.items()):
        cat_dir = DST / cat
        cat_dir.mkdir(exist_ok=True)
        manifest[cat] = []
        print(f"\n📁 {cat}/ ({len(items)}개)")
        # 같은 라벨 중복 시 번호 붙이기
        label_counts = {}
        for f, label, cat_label in items:
            key = label
            if label_counts.get(key, 0) > 0:
                key = f"{label} ②" if label_counts[key] == 1 else f"{label} ③"
            label_counts[label] = label_counts.get(label, 0) + 1
            # 안전한 파일명
            safe_name = f"{cat}-{len(manifest[cat]) + 1:02d}{f.suffix}"
            dst_path = cat_dir / safe_name
            shutil.copy2(str(f), str(dst_path))
            manifest[cat].append({
                'id': f"{cat}-{len(manifest[cat]) + 1:02d}",
                'file': f"ambience/{cat}/{safe_name}",
                'label': key,
                'category': cat,
                'category_label': cat_label,
                'original': f.name,
            })
            print(f"   ✓ {safe_name:18s} ← {key}")

    # manifest 저장 (브라우저에서 fetch 가능하도록)
    manifest_path = DST / 'manifest.json'
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"\n📋 manifest: {manifest_path}")
    print(f"\n총 {sum(len(v) for v in manifest.values())} 트랙 / {len(manifest)} 카테고리")


if __name__ == '__main__':
    main()
