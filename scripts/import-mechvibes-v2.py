"""
Mechvibes 팩 → Key Therapy 팩 (single / multi 두 형식 모두 지원).

single: 한 sound.ogg 안에 모든 키 → defines: {key: [start_ms, duration_ms]}
multi:  키별로 개별 파일 → defines: {key: "filename.wav"}
"""
import json
import sys
import numpy as np
import soundfile as sf
import scipy.io.wavfile as wavfile
from scipy import signal
from pathlib import Path


PREFERRED_KEYS = ['a', 's', 'd', 'f', 'j', 'k', 'l', ';', 'space', 'enter']
FALLBACK_KEYS = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0',
                 'q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p',
                 'z', 'x', 'c', 'v', 'b', 'n', 'm']


def gentle_cleanup(d, sr):
    """매우 가벼운 정리."""
    if len(d) < int(sr * 0.02):
        return d
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
    nyq = sr / 2
    sos = signal.butter(2, 60 / nyq, btype='highpass', output='sos')
    d = signal.sosfiltfilt(sos, d)
    fade_n = max(1, int(sr * 0.005))
    if len(d) > fade_n * 2:
        d = d.copy()
        d[-fade_n:] *= np.linspace(1, 0, fade_n) ** 2
    peak = np.abs(d).max()
    if peak > 1e-9:
        d = d * (10 ** (-3 / 20)) / peak
    return d


def load_audio(path):
    """모든 형식 로드 → mono float64, sr."""
    try:
        audio, sr = sf.read(str(path))
    except Exception as e:
        print(f"     ⚠️  {path.name} 로드 실패: {e}")
        return None, None
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    audio = audio.astype(np.float64)
    return audio, sr


def resample_if_needed(audio, sr_in, sr_out=48000):
    if sr_in == sr_out:
        return audio, sr_in
    from scipy.signal import resample_poly
    audio = resample_poly(audio, sr_out, sr_in)
    return audio, sr_out


def select_keys(defines):
    """defines 에서 10개 키 선택."""
    selected = []
    seen = set()
    for k in PREFERRED_KEYS:
        if k in defines and defines[k] is not None:
            selected.append(k)
            seen.add(k)
            if len(selected) >= 10:
                return selected
    for k in FALLBACK_KEYS:
        if k in defines and defines[k] is not None and k not in seen:
            selected.append(k)
            seen.add(k)
            if len(selected) >= 10:
                return selected
    for k, v in defines.items():
        if k not in seen and v is not None:
            selected.append(k)
            seen.add(k)
            if len(selected) >= 10:
                return selected
    return selected[:10]


def extract_single(pack_folder, config, sound_path):
    """Single mode: 한 파일 + 타이밍 정보."""
    audio, sr = load_audio(sound_path)
    if audio is None:
        return None
    audio, sr = resample_if_needed(audio, sr)
    defines = config.get('defines', {})
    keys = select_keys(defines)
    clips = []
    for key in keys[:10]:
        timing = defines[key]
        if not timing or not isinstance(timing, list) or len(timing) < 2:
            continue
        start_ms, duration_ms = timing[0], timing[1]
        start = int(start_ms * sr / 1000)
        duration = int(duration_ms * sr / 1000)
        end = min(start + duration, len(audio))
        if start >= end or end - start < 100:
            continue
        clip = audio[start:end].copy()
        clips.append((key, clip, sr))
    return clips


def extract_multi(pack_folder, config, sound_filename_hint):
    """Multi mode: 키별 개별 파일."""
    defines = config.get('defines', {})
    keys = select_keys(defines)
    clips = []
    for key in keys[:10]:
        fname = defines[key]
        if not isinstance(fname, str):
            continue
        # 정확한 파일명 시도 → 없으면 hint(sound 필드 기반) 패턴 시도
        candidates = [
            pack_folder / fname,
            pack_folder / fname.lower(),
        ]
        # mechvibes 가 종종 .ogg → .wav 표기 차이 → 둘 다 시도
        for ext_alt in ['.wav', '.ogg', '.mp3', '.flac']:
            stem = Path(fname).stem
            candidates.append(pack_folder / f"{stem}{ext_alt}")
            candidates.append(pack_folder / f"{stem.lower()}{ext_alt}")
        path = next((p for p in candidates if p.exists()), None)
        if path is None:
            continue
        audio, sr = load_audio(path)
        if audio is None:
            continue
        audio, sr = resample_if_needed(audio, sr)
        if len(audio) < 100:
            continue
        clips.append((key, audio, sr))
    return clips


def fill_to_10(clips, target=10):
    """클립이 10개 안 되면 pitch shift 변형으로 채움."""
    if len(clips) >= target or len(clips) == 0:
        return clips[:target]
    from scipy.signal import resample
    base_clips = list(clips)
    while len(clips) < target:
        idx = len(clips)
        src_key, src_audio, src_sr = base_clips[idx % len(base_clips)]
        # Pitch shift via resample (시간도 같이 변함)
        stretch_factor = 0.93 + ((idx * 13) % 10) * 0.015  # 0.93~1.07
        new_len = max(8, int(len(src_audio) / stretch_factor))
        stretched = resample(src_audio, new_len)
        clips.append((f"{src_key}_v{idx}", stretched, src_sr))
    return clips


def import_pack(pack_folder, dest_pack_num, dest_root):
    pack_folder = Path(pack_folder)
    config_path = pack_folder / 'config.json'
    if not config_path.exists():
        print(f"     ❌ config.json 없음")
        return False
    with open(config_path) as f:
        config = json.load(f)
    print(f"  📦 {pack_folder.name}: {config.get('name', '?')}")
    define_type = config.get('key_define_type', 'single')
    sound_field = config.get('sound', 'sound.ogg')

    if define_type == 'single':
        sound_path = pack_folder / sound_field
        if not sound_path.exists():
            # 폴더 안에서 첫 audio file 찾기
            for ext in ['.ogg', '.wav', '.mp3', '.flac']:
                cands = list(pack_folder.glob(f'*{ext}'))
                if cands:
                    sound_path = cands[0]
                    break
        if not sound_path.exists():
            print(f"     ❌ sound 파일 없음")
            return False
        clips = extract_single(pack_folder, config, sound_path)
    else:  # multi
        clips = extract_multi(pack_folder, config, sound_field)

    if not clips:
        print(f"     ❌ 추출된 클립 0개")
        return False

    clips = fill_to_10(clips, 10)
    out_dir = Path(dest_root) / str(dest_pack_num)
    out_dir.mkdir(parents=True, exist_ok=True)
    n_done = 0
    for i, (key, clip, sr) in enumerate(clips, 1):
        if sr != 48000:
            clip, sr = resample_if_needed(clip, sr, 48000)
        clip = gentle_cleanup(clip, sr)
        if len(clip) < int(sr * 0.02):
            continue
        out_path = out_dir / f'{dest_pack_num} ({i}).wav'
        wavfile.write(str(out_path), sr, clip.astype(np.float32))
        n_done += 1
    print(f"     ✅ Pack {dest_pack_num}: {n_done}/10")
    return n_done > 0


# Batch mapping — 13 슬롯에 진짜 키보드 사운드만
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


def main():
    base = Path('newsound')
    dest = 'public/soundFiles'
    n_ok, n_fail = 0, 0
    print("=" * 65)
    print("13개 키보드 사운드팩 자동 매핑 (single + multi 형식 지원)")
    print("=" * 65)
    for slot, folder, label in MAPPING:
        folder_path = base / folder
        print(f"\n  Slot {slot:2d} → {label}")
        if not folder_path.exists():
            print(f"     ❌ {folder} 폴더 없음")
            n_fail += 1
            continue
        try:
            ok = import_pack(str(folder_path), slot, dest)
            (n_ok if ok else n_fail).__add__
            if ok:
                n_ok += 1
            else:
                n_fail += 1
        except Exception as e:
            print(f"     ❌ 에러: {e}")
            import traceback; traceback.print_exc()
            n_fail += 1
    print("\n" + "=" * 65)
    print(f"DONE: {n_ok} 성공 / {n_fail} 실패 / 총 {len(MAPPING)}")
    print("=" * 65)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--single':
        # 개별 호출: --single <folder> <slot>
        import_pack(sys.argv[2], int(sys.argv[3]), 'public/soundFiles')
    else:
        main()
