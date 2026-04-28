"""
앰비언스 트랙 마스터링 — loop 친화 + 음량 일관 + 메타 정리.

처리:
  1. ffmpeg loudnorm (EBU R128) — target I=-23 LUFS (편안한 배경음)
  2. 짧은 fade in 60ms — loop 시작 시 클릭 방지
  3. 메타데이터 제거 (-map_metadata -1) — 깨끗한 헤더
  4. MP3 V3 재인코딩 — 품질 유지 + 약 96~128kbps
  5. 시작/끝 무음 트림 — silenceremove (선택)

대상: public/ambience/*/*.mp3 + *.wav
"""
import os
import sys
import json
import shutil
import subprocess
from pathlib import Path


SRC = Path('public/ambience')


def get_duration(path):
    """ffprobe 로 길이 (초)."""
    try:
        out = subprocess.check_output([
            'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', str(path)
        ], text=True).strip()
        return float(out)
    except Exception as e:
        return None


def master_track(in_path, out_path):
    """단일 트랙 마스터링 — loudnorm + fade-in + 메타 정리."""
    dur = get_duration(in_path)
    if not dur or dur < 0.5:
        return False, 'too short'

    # 빌드 필터 체인
    filters = []
    # 1. silenceremove — 시작 무음만 제거 (끝은 loop 위해 보존)
    filters.append('silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.1')
    # 2. fade in — loop 시작 클릭 방지
    filters.append('afade=t=in:st=0:d=0.06')
    # 3. loudnorm — EBU R128 정규화, target -23 LUFS
    filters.append('loudnorm=I=-23:TP=-2:LRA=11')

    af = ','.join(filters)
    cmd = [
        'ffmpeg', '-y', '-loglevel', 'error',
        '-i', str(in_path),
        '-af', af,
        '-map_metadata', '-1',
        '-id3v2_version', '0',
        '-codec:a', 'libmp3lame',
        '-q:a', '4',  # ~128~165kbps VBR
        str(out_path),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        return True, None
    except subprocess.CalledProcessError as e:
        return False, e.stderr[:200]


def main():
    if not SRC.exists():
        print(f"❌ {SRC} 없음")
        return
    # 임시 출력 디렉토리 (덮어쓰기 안전)
    tmp = SRC / '_mastered_tmp'
    tmp.mkdir(exist_ok=True)

    n_done = 0
    n_skip = 0
    n_fail = 0
    by_cat_results = {}

    audio_exts = ('.mp3', '.wav', '.ogg')
    files = []
    for cat_dir in sorted(SRC.iterdir()):
        if cat_dir.is_dir() and cat_dir.name not in ('_mastered_tmp',):
            for f in sorted(cat_dir.iterdir()):
                if f.suffix.lower() in audio_exts:
                    files.append(f)

    print(f"마스터링 대상: {len(files)} 트랙")
    print(f"target: -23 LUFS · 60ms fade-in · MP3 V4")
    print(f"시작...\n")

    for f in files:
        rel = f.relative_to(SRC)
        cat = rel.parts[0]
        out_path = tmp / cat / (f.stem + '.mp3')
        out_path.parent.mkdir(parents=True, exist_ok=True)
        ok, err = master_track(f, out_path)
        cat_res = by_cat_results.setdefault(cat, {'done': 0, 'fail': 0})
        if ok:
            n_done += 1
            cat_res['done'] += 1
            print(f"  ✓ {rel}")
        else:
            n_fail += 1
            cat_res['fail'] += 1
            print(f"  ✗ {rel}  — {err}")

    # 임시 → 원본 위치로 이동 (덮어쓰기)
    print(f"\n원본 위치로 이동 중...")
    for cat_tmp in tmp.iterdir():
        if not cat_tmp.is_dir():
            continue
        for f in cat_tmp.iterdir():
            target = SRC / cat_tmp.name / f.name
            try:
                shutil.copy2(str(f), str(target))
            except Exception as e:
                print(f"  ⚠️  {target} 이동 실패: {e}")
    # 임시 디렉토리는 cowork 환경에서 삭제 안 될 수 있음 — 그대로 둠

    print(f"\n완료: {n_done} 성공 / {n_fail} 실패 / 총 {len(files)}")
    print(f"\n카테고리별:")
    for cat, r in sorted(by_cat_results.items()):
        print(f"  {cat:10s}: {r['done']:2d} 성공 / {r['fail']} 실패")


if __name__ == '__main__':
    main()
