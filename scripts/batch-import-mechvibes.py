"""
13개 슬롯에 진짜 키보드 사운드팩 일괄 매핑.

선정 기준: 텍스처 다양성 (가벼움 → 묵직 → 클릭 → 빈티지)
        + 게임/밈 사운드 (ACNL, AMOGUS, Bruh 등) 제외
"""
import sys
sys.path.insert(0, '.')
from pathlib import Path
import importlib.util
spec = importlib.util.spec_from_file_location("im", "scripts/import-mechvibes-pack.py")
im = importlib.util.module_from_spec(spec)
spec.loader.exec_module(im)


# (slot_number, mechvibes_folder_name, character_label)
MAPPING = [
    (1,  'mx-speed-silver',           '⚡ 가벼운 빠른 (Speed Silver)'),
    (2,  'cherrymx-red-pbt',          '🌊 부드러운 (MX Red PBT)'),
    (3,  'Gateron Black Ink - Revolt','🔘 매끈 서걱 (Gateron Black Ink)'),
    (4,  'cherrymx-brown-pbt',        '🟫 텍타일 (MX Brown PBT)'),
    (5,  'banana split lubed',        '🍌 윤활 텍타일 (Banana Split Lubed)'),
    (6,  'holy-pandas',               '🐼 도각도각 (Holy Pandas)'),
    (7,  'cherrymx-blue-pbt',         '🔵 클릭 (MX Blue PBT)'),
    (8,  'boxjade',                   '🟢 찰칵 (Box Jade)'),
    (9,  'cherrymx-black-pbt',        '⚫ 묵직 (MX Black PBT)'),
    (10, 'nk-cream',                  '🥛 POM 서걱 (NK Cream)'),
    (11, 'topre-purple-hybrid-pbt',   '💜 부드러운 톡톡 (Topre)'),
    (12, 'eg-oreo',                   '🍪 트렌디 (Oreo)'),
    (13, 'Teleprinter',               '📠 빈티지 타자기 (Teleprinter)'),
]

BASE = Path('newsound')
DEST = 'public/soundFiles'

if __name__ == '__main__':
    n_ok = 0
    n_fail = 0
    print("=" * 60)
    print("13개 키보드 사운드팩 자동 매핑")
    print("=" * 60)
    for slot, folder, label in MAPPING:
        folder_path = BASE / folder
        if not folder_path.exists():
            print(f"\n  ❌ Slot {slot:2d}: {folder} 폴더 없음")
            n_fail += 1
            continue
        print(f"\n  Slot {slot:2d} → {label}")
        try:
            ok = im.import_pack(str(folder_path), slot, DEST)
            if ok:
                n_ok += 1
            else:
                n_fail += 1
        except Exception as e:
            print(f"     ❌ 에러: {e}")
            n_fail += 1
    print("\n" + "=" * 60)
    print(f"DONE: {n_ok} 성공 / {n_fail} 실패 / 총 {len(MAPPING)}")
    print("=" * 60)
