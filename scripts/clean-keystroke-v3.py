"""
타건음 v3 — 미니멀 정리, 원본 캐릭터 최대 보존.

v2 의 문제: Wiener + EQ + gate 가 자연스러움 손상 → 합성된 듯한 느낌.
v3 철학: "녹음의 진짜 캐릭터를 살리되, 가장 큰 잡음만 제거".

처리:
  1. 시작·끝 무음 트림 (보수적, 5ms 패드)
  2. 약한 HP at 80Hz (마이크 럼블만 제거)
  3. 매우 가벼운 노이즈 게이트 (-12dB only, 부드럽게)
  4. 1ms fade in / 4ms fade out
  5. Peak -3dB normalize

— EQ 컷 / Wiener 차감 / spectral 처리 없음
— 원본의 톤·디테일·룸 톤 모두 보존
"""
import os
import sys
import numpy as np
import scipy.io.wavfile as wavfile
from scipy import signal
from pathlib import Path


def to_float(d):
    if np.issubdtype(d.dtype, np.floating):
        return d.astype(np.float64), 'float'
    info = np.iinfo(d.dtype)
    f = d.astype(np.float64) / max(abs(info.min), info.max)
    return f, str(d.dtype)


def to_pcm(f, target_dtype):
    if target_dtype == 'float':
        return f.astype(np.float32)
    info = np.iinfo(np.dtype(target_dtype))
    scaled = np.clip(f, -1.0, 1.0) * info.max
    return scaled.astype(target_dtype)


def trim_silence_gentle(d, sr, threshold_pct=0.025, edge_pad_ms=5):
    """매우 보수적인 트림 — 자연스러운 원본 길이 보존."""
    win = max(1, int(sr * 0.003))
    if len(d) < win * 4:
        return d
    sq = d ** 2
    cumsum = np.cumsum(sq)
    rms = np.sqrt((cumsum[win:] - cumsum[:-win]) / win)
    threshold = rms.max() * threshold_pct
    above = np.where(rms > threshold)[0]
    if len(above) == 0:
        return d
    pad = int(sr * edge_pad_ms / 1000)
    start = max(0, above[0] - pad)
    end = min(len(d), above[-1] + win + pad)
    return d[start:end]


def light_highpass(d, sr, cutoff=80):
    """매우 가벼운 HP — 8dB/oct (1차 + 1차)."""
    nyq = sr / 2
    sos = signal.butter(2, cutoff / nyq, btype='highpass', output='sos')
    return signal.sosfiltfilt(sos, d)


def gentle_gate(d, sr, threshold_pct=0.025, attenuation_db=-12):
    """가벼운 expansion — 임계 이하 -12dB만 감쇠 (-30dB 게이트가 아님).

    원본의 자연스러운 잔향·룸 톤이 살아있음.
    """
    win = max(1, int(sr * 0.002))
    sq = d ** 2
    cumsum = np.cumsum(sq)
    env = np.zeros_like(d)
    env[win:] = np.sqrt((cumsum[win:] - cumsum[:-win]) / win)
    env[:win] = env[win] if win < len(env) else 0
    threshold = env.max() * threshold_pct
    # Soft expansion 곡선
    target_lin = 10 ** (attenuation_db / 20)
    gain = np.where(env > threshold, 1.0, target_lin)
    # 부드러운 평활화 — attack 1ms, release 30ms (자연스럽게)
    attack_n = max(1, int(0.001 * sr))
    release_n = max(1, int(0.030 * sr))
    smoothed = np.zeros_like(gain)
    smoothed[0] = gain[0]
    for i in range(1, len(gain)):
        if gain[i] < smoothed[i - 1]:
            alpha = 1.0 / release_n
        else:
            alpha = 1.0 / attack_n
        smoothed[i] = smoothed[i - 1] + alpha * (gain[i] - smoothed[i - 1])
    return d * smoothed


def fade(d, sr, fade_in_ms=1, fade_out_ms=4):
    n_in = max(1, int(sr * fade_in_ms / 1000))
    n_out = max(1, int(sr * fade_out_ms / 1000))
    if len(d) < (n_in + n_out) * 2:
        return d
    fade_in = np.linspace(0, 1, n_in) ** 1.5
    fade_out = np.linspace(1, 0, n_out) ** 2
    d = d.copy()
    d[:n_in] *= fade_in
    d[-n_out:] *= fade_out
    return d


def normalize_peak(d, target_db=-3.0):
    target = 10 ** (target_db / 20)
    peak = np.abs(d).max()
    if peak < 1e-9:
        return d
    return d * (target / peak)


def clean_v3(d, sr):
    d = trim_silence_gentle(d, sr)
    if len(d) < sr * 0.05:
        return None
    d = light_highpass(d, sr, cutoff=80)
    d = gentle_gate(d, sr)
    d = fade(d, sr)
    d = normalize_peak(d, -3.0)
    return d


def process_file(in_path, out_path):
    sr, d = wavfile.read(in_path)
    if d.ndim > 1:
        d = d[:, 0]
    d_f, dtype_str = to_float(d)
    cleaned = clean_v3(d_f, sr)
    if cleaned is None:
        wavfile.write(out_path, sr, d)
        return False
    out_int = to_pcm(cleaned, dtype_str if dtype_str != 'float' else np.float32)
    wavfile.write(out_path, sr, out_int)
    return True


def main(src_root, dst_root):
    src_root = Path(src_root)
    dst_root = Path(dst_root)
    if not src_root.exists():
        print(f"ERROR: {src_root} 없음.")
        sys.exit(1)
    n_done, n_skip = 0, 0
    for pack in sorted(src_root.iterdir(), key=lambda p: int(p.name) if p.name.isdigit() else 99):
        if not pack.is_dir():
            continue
        for wav in sorted(pack.glob('*.wav')):
            rel = wav.relative_to(src_root)
            dst = dst_root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            ok = process_file(str(wav), str(dst))
            if ok:
                n_done += 1
            else:
                n_skip += 1
    print(f"DONE v3: {n_done} processed, {n_skip} skipped (gentle cleanup)")


if __name__ == '__main__':
    src = sys.argv[1] if len(sys.argv) > 1 else 'api/public/soundFiles'
    dst = sys.argv[2] if len(sys.argv) > 2 else 'public/soundFiles'
    main(src, dst)
