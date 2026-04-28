"""
Mechvibes 사운드 팩 → Key Therapy 팩 형식으로 변환.

입력: Mechvibes 폴더 (sound.ogg + config.json)
출력: public/soundFiles/{팩번호}/{팩번호} (1~10).wav

config.json 의 defines 에서 가장 많이 쓰이는 key 10개 골라서 분할.
"""
import json
import sys
import numpy as np
import soundfile as sf
import scipy.io.wavfile as wavfile
from scipy import signal
from pathlib import Path


# 가장 자주 쓰이는 영문 키 10개 (한글 자주 매핑되는 것들 우선)
PREFERRED_KEYS = ['a', 's', 'd', 'f', 'j', 'k', 'l', ';', 'space', 'enter']
# fallback — 위에 매칭 안 되면 이걸로
FALLBACK_KEYS = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0']


def extract_key_sound(audio, sr, start_ms, duration_ms):
    """sound.ogg 안에서 특정 키 구간 잘라내기."""
    start = int(start_ms * sr / 1000)
    duration = int(duration_ms * sr / 1000)
    end = start + duration
    if start >= len(audio) or end > len(audio):
        end = min(end, len(audio))
        if start >= end:
            return None
    return audio[start:end].copy()


def gentle_cleanup(d, sr):
    """매우 가벼운 정리 — 원본 캐릭터 보존."""
    if len(d) < int(sr * 0.02):
        return d
    # 1. Trim trailing silence (시작은 그대로 두기 — transient 보존)
    win = max(1, int(sr * 0.003))
    sq = d ** 2
    cumsum = np.cumsum(sq)
    rms = np.sqrt((cumsum[win:] - cumsum[:-win]) / win)
    if len(rms) > 0:
        threshold = rms.max() * 0.03
        above = np.where(rms > threshold)[0]
        if len(above) > 0:
            end = min(len(d), above[-1] + win + int(sr * 0.005))
            d = d[:end]
    # 2. 매우 가벼운 HP at 60Hz (DC offset + 럼블만)
    nyq = sr / 2
    sos = signal.butter(2, 60 / nyq, btype='highpass', output='sos')
    d = signal.sosfiltfilt(sos, d)
    # 3. Fade out 5ms (cutoff click 방지)
    fade_n = max(1, int(sr * 0.005))
    if len(d) > fade_n * 2:
        d = d.copy()
        d[-fade_n:] *= np.linspace(1, 0, fade_n) ** 2
    # 4. Peak normalize -3dB
    peak = np.abs(d).max()
    if peak > 1e-9:
        d = d * (10 ** (-3 / 20)) / peak
    return d


def select_keys(defines):
    """defines 에서 10개 키 선택. PREFERRED 우선, 부족하면 FALLBACK + 처음부터 추가."""
    selected = []
    seen = set()
    for k in PREFERRED_KEYS:
        if k in defines and k not in seen:
            selected.append(k)
            seen.add(k)
            if len(selected) >= 10:
                return selected
    for k in FALLBACK_KEYS:
        if k in defines and k not in seen:
            selected.append(k)
            seen.add(k)
            if len(selected) >= 10:
                return selected
    # Still not enough — fill with arbitrary keys
    for k in defines.keys():
        if k not in seen:
            selected.append(k)
            seen.add(k)
            if len(selected) >= 10:
                return selected
    return selected[:10]


def import_pack(pack_folder, dest_pack_num, dest_root):
    """Mechvibes 팩 하나를 Key Therapy 팩 형식으로 변환."""
    pack_folder = Path(pack_folder)
    config_path = pack_folder / 'config.json'
    sound_path = pack_folder / 'sound.ogg'
    if not config_path.exists():
        print(f"  ❌ {pack_folder.name}: config.json 없음")
        return False
    if not sound_path.exists():
        print(f"  ❌ {pack_folder.name}: sound.ogg 없음")
        return False

    with open(config_path) as f:
        config = json.load(f)

    print(f"  📦 {pack_folder.name}: {config.get('name', '?')}")
    audio, sr = sf.read(str(sound_path))
    if audio.ndim > 1:
        audio = audio.mean(axis=1)  # mono mix

    # Resample to 48kHz if needed (원본 키테라피 포맷)
    if sr != 48000:
        from scipy.signal import resample_poly
        audio = resample_poly(audio, 48000, sr)
        sr = 48000

    defines = config.get('defines', {})
    keys = select_keys(defines)
    if len(keys) == 0:
        print(f"     ❌ defines 비어있음")
        return False

    out_dir = Path(dest_root) / str(dest_pack_num)
    out_dir.mkdir(parents=True, exist_ok=True)

    n_done = 0
    for i, key in enumerate(keys[:10], 1):
        timing = defines[key]
        if not timing or len(timing) < 2:
            continue
        start_ms, duration_ms = timing[0], timing[1]
        clip = extract_key_sound(audio, sr, start_ms, duration_ms)
        if clip is None or len(clip) < 100:
            continue
        clip = gentle_cleanup(clip, sr)
        out_path = out_dir / f'{dest_pack_num} ({i}).wav'
        # 32-bit float WAV (원본 포맷과 동일)
        wavfile.write(str(out_path), sr, clip.astype(np.float32))
        n_done += 1

    # 10개 안 채워졌으면 같은 파일 cycle 로 채움 (대기 sample 없음 방지)
    if n_done < 10 and n_done > 0:
        existing = sorted(out_dir.glob(f'{dest_pack_num} (*).wav'))
        for i in range(n_done + 1, 11):
            src = existing[(i - 1) % n_done]
            dst = out_dir / f'{dest_pack_num} ({i}).wav'
            # 약간 다른 효과를 위해 미세 pitch shift (시간 도메인 stretch)
            sr_in, d = wavfile.read(str(src))
            if d.ndim > 1: d = d[:, 0]
            d_f = d.astype(np.float64) if np.issubdtype(d.dtype, np.floating) else d.astype(np.float64) / np.iinfo(d.dtype).max
            stretch_factor = 0.95 + ((i * 13) % 10) * 0.012  # 0.95~1.06
            new_len = max(8, int(len(d_f) / stretch_factor))
            from scipy.signal import resample
            stretched = resample(d_f, new_len)
            # peak normalize
            peak = np.abs(stretched).max()
            if peak > 1e-9:
                stretched = stretched * (10 ** (-3 / 20)) / peak
            wavfile.write(str(dst), sr_in, stretched.astype(np.float32))
            n_done += 1

    print(f"     ✅ Pack {dest_pack_num}: {n_done}/10 keys → {out_dir}")
    return True


def main():
    if len(sys.argv) < 4:
        print("Usage: python3 import-mechvibes-pack.py <mechvibes_folder> <dest_pack_num> <dest_root>")
        print("       <mechvibes_folder>: e.g. cherrymx-black-abs")
        print("       <dest_pack_num>: 1~13")
        print("       <dest_root>: e.g. public/soundFiles")
        sys.exit(1)
    pack_folder = sys.argv[1]
    pack_num = int(sys.argv[2])
    dest_root = sys.argv[3]
    import_pack(pack_folder, pack_num, dest_root)


if __name__ == '__main__':
    main()
