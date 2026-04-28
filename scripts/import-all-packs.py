"""
모든 진짜 키보드 사운드팩을 슬롯 1~N에 연속 매핑.

게임/밈 팩 (ACNL, AMOGUS, Bruh 등) 제외.
Sound 파일 없는 placeholder ZIP (boxnavy, bluealps, blackink) 제외.
"""
import sys
sys.path.insert(0, '.')
from pathlib import Path
import importlib.util
spec = importlib.util.spec_from_file_location("im", "scripts/import-mechvibes-v2.py")
im = importlib.util.module_from_spec(spec)
spec.loader.exec_module(im)


# 26개 진짜 키보드 팩 (큐레이션 순서: 가벼움 → 텍타일 → 클릭 → 묵직 → POM → Topre → 게이밍 → 빈티지)
KEYBOARD_PACKS = [
    # 1군: 가벼운 linear (3)
    ('mx-speed-silver',                       '⚡ Speed Silver'),
    ('cherrymx-red-abs',                       '🌿 MX Red ABS'),
    ('cherrymx-red-pbt',                       '🌊 MX Red PBT'),
    # 2군: 텍타일 (7)
    ('cherrymx-brown-abs',                     '🟫 MX Brown ABS'),
    ('cherrymx-brown-pbt',                     '🟫 MX Brown PBT'),
    ('Gateron Browns - Revolt',                '🟤 Gateron Brown'),
    ('banana split stock',                     '🍌 Banana Split Stock'),
    ('banana split lubed',                     '🍌 Banana Split Lubed'),
    ('holy-pandas',                            '🐼 Holy Pandas'),
    ('Glorious panda',                         '🐼 Glorious Panda'),
    # 3군: 클릭 (3)
    ('cherrymx-blue-abs',                      '🔵 MX Blue ABS'),
    ('cherrymx-blue-pbt',                      '🔵 MX Blue PBT'),
    ('boxjade',                                '🟢 Box Jade'),
    # 4군: 묵직 / heavy linear (3)
    ('cherrymx-black-abs',                     '⚫ MX Black ABS'),
    ('cherrymx-black-pbt',                     '⚫ MX Black PBT'),
    ('Gateron Reds - Revolt',                  '🔴 Gateron Red'),
    # 5군: POM / 모던 smooth (3)
    ('nk-cream',                               '🥛 NK Cream'),
    ('eg-oreo',                                '🍪 EG Oreo'),
    ('eg-crystal-purple',                      '💎 EG Crystal Purple'),
    # 6군: Topre (1)
    ('topre-purple-hybrid-pbt',                '💜 Topre Purple Hybrid'),
    # 7군: 게이밍/노트북 (3)
    ('HyperX Alloy Origins Aqua Switches',     '🎮 HyperX Aqua'),
    ('steelseries apex pro tkl',               '🎯 SteelSeries Apex Pro'),
    ('opera-gx-typing-sounds',                 '🦁 Opera GX'),
    # 8군: 빈티지 (3)
    ('Lincoln Typewriter',                     '📜 Lincoln Typewriter'),
    ('Teleprinter',                            '📠 Teleprinter'),
    ('Minimal Tick Edit',                      '⚪ Minimal Tick'),
]


def main():
    base = Path('newsound')
    dest = 'public/soundFiles'
    n_ok, n_fail = 0, 0
    print("=" * 70)
    print(f"전체 {len(KEYBOARD_PACKS)}개 진짜 키보드 팩 → 슬롯 1~{len(KEYBOARD_PACKS)}")
    print("=" * 70)
    success_packs = []
    for slot, (folder, label) in enumerate(KEYBOARD_PACKS, 1):
        folder_path = base / folder
        print(f"\n  Slot {slot:2d}: {label}")
        if not folder_path.exists():
            print(f"     ❌ 폴더 없음")
            n_fail += 1
            continue
        try:
            ok = im.import_pack(str(folder_path), slot, dest)
            if ok:
                n_ok += 1
                success_packs.append((slot, label))
            else:
                n_fail += 1
        except Exception as e:
            print(f"     ❌ 에러: {e}")
            n_fail += 1
    print("\n" + "=" * 70)
    print(f"DONE: {n_ok} 성공 / {n_fail} 실패 / 총 {len(KEYBOARD_PACKS)}")
    print("=" * 70)
    return n_ok, success_packs


if __name__ == '__main__':
    main()
