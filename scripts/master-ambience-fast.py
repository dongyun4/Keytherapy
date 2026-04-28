"""
앰비언스 라이트 마스터링 — 병렬·빠른 처리.

처리 (트랙당 ~3초):
  1. volumedetect 로 max peak 측정 (1패스)
  2. peak → -3dBFS 정규화 gain 계산
  3. ffmpeg: gain 적용 + 60ms fade-in + 메타 제거 + MP3 V4 재인코딩

  loudnorm 의 EBU 정규화는 생략 (UI 믹서에서 사용자가 트랙별 볼륨 조절 가능).
  대신 모든 파일이 비슷한 peak로 정렬돼 mixer 에서 시작점이 균등.
"""
import os
import re
import subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

SRC = Path('public/ambience')


def get_peak_db(path):
    """ffmpeg volumedetect 로 max_volume 측정 (dBFS)."""
    try:
        result = subprocess.run([
            'ffmpeg', '-hide_banner', '-i', str(path),
            '-af', 'volumedetect', '-vn', '-f', 'null', '-'
        ], capture_output=True, text=True, timeout=120)
        m = re.search(r'max_volume:\s*(-?\d+\.\d+)\s*dB', result.stderr)
        if m:
            return float(m.group(1))
    except Exception:
        pass
    return None


def master_one(path):
    """단일 트랙 처리. 병렬 worker 에서 호출."""
    peak = get_peak_db(path)
    if peak is None:
        return (path, False, 'volumedetect 실패')
    # Gain to bring peak to -3dBFS
    gain_db = -3.0 - peak
    # 너무 큰 boost 제한 (+12dB 이상 X)
    gain_db = max(min(gain_db, 12.0), -20.0)

    out_path = path.with_suffix('.mastered.mp3')
    cmd = [
        'ffmpeg', '-y', '-loglevel', 'error',
        '-i', str(path),
        '-af', f'volume={gain_db:.2f}dB,afade=t=in:st=0:d=0.06',
        '-map_metadata', '-1',
        '-id3v2_version', '0',
        '-codec:a', 'libmp3lame',
        '-q:a', '4',
        str(out_path),
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=120)
        # 원본 위치로 덮어쓰기 (이름 다시 변경)
        # cowork 에서 rm 권한 제약 → mv 대신 read+write 로 덮어쓰기
        with open(out_path, 'rb') as src:
            data = src.read()
        # 원본 확장자가 .wav 였다면 .mp3 로 변경하기 위해 새 파일 작성
        target = path.with_suffix('.mp3')
        with open(target, 'wb') as dst:
            dst.write(data)
        # 임시 .mastered.mp3 는 그대로 두거나 삭제 시도
        try:
            out_path.unlink()
        except Exception:
            pass
        return (path, True, f'peak {peak:+.1f} → -3dB (gain {gain_db:+.1f}dB)')
    except subprocess.CalledProcessError as e:
        return (path, False, e.stderr[:150])
    except Exception as e:
        return (path, False, str(e)[:150])


def main():
    if not SRC.exists():
        print(f"❌ {SRC} 없음")
        return

    audio_exts = ('.mp3', '.wav', '.ogg')
    files = []
    for cat_dir in sorted(SRC.iterdir()):
        if cat_dir.is_dir() and cat_dir.name not in ('_mastered_tmp',):
            for f in sorted(cat_dir.iterdir()):
                if f.suffix.lower() in audio_exts and not f.stem.endswith('.mastered'):
                    files.append(f)

    print(f"마스터링: {len(files)} 트랙 (병렬 6 workers)")
    print(f"target: peak -3dBFS, fade-in 60ms, MP3 V4\n")

    n_done = n_fail = 0
    with ThreadPoolExecutor(max_workers=6) as ex:
        for path, ok, msg in ex.map(master_one, files):
            rel = path.relative_to(SRC)
            if ok:
                n_done += 1
                print(f"  ✓ {rel}  [{msg}]")
            else:
                n_fail += 1
                print(f"  ✗ {rel}  — {msg}")

    print(f"\n완료: {n_done}/{len(files)} 성공, {n_fail} 실패")


if __name__ == '__main__':
    main()
