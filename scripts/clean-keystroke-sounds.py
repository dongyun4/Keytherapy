"""
타건음 .wav 파일 노이즈 정리 + 마스터링.

처리 단계:
  1. Trim silence — 시작·끝 무음 구간 제거
  2. Spectral noise subtraction — STFT 기반 노이즈 차감 (시작·끝의 노이즈 프로파일 사용)
  3. Bandpass filter — 60Hz HP (럼블) + 14kHz LP (hiss)
  4. Noise gate — 임계 이하 신호 부드럽게 감쇠
  5. Fade in/out 3ms — 클릭 노이즈 방지
  6. Normalize — peak -3dB (0.71)

원본은 public/soundFiles_original/ 에 백업되어 있음.
"""
import os
import sys
import numpy as np
import scipy.io.wavfile as wavfile
from scipy import signal
from pathlib import Path


def to_float(d):
    """integer PCM → float [-1, 1]"""
    if np.issubdtype(d.dtype, np.floating):
        return d.astype(np.float64), 'float'
    info = np.iinfo(d.dtype)
    # 32-bit signed: divide by max
    f = d.astype(np.float64) / max(abs(info.min), info.max)
    return f, str(d.dtype)


def to_pcm(f, target_dtype):
    """float [-1, 1] → integer PCM (원본 dtype 보존)"""
    if target_dtype == 'float':
        return f.astype(np.float32)
    info = np.iinfo(np.dtype(target_dtype))
    scaled = np.clip(f, -1.0, 1.0) * info.max
    return scaled.astype(target_dtype)


def trim_silence(d, sr, threshold_pct=0.04, edge_pad_ms=4):
    """RMS 기반 시작·끝 무음 트림. edge_pad_ms 만큼 여유 둠."""
    win = max(1, int(sr * 0.003))  # 3ms 윈도우
    if len(d) < win * 4:
        return d
    # 짧은 윈도우 RMS
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


def estimate_noise_profile(d, sr, n_fft=1024):
    """파일의 가장 조용한 30ms 구간을 탐지 → STFT magnitude 평균을 노이즈 프로파일로."""
    win = max(1, int(sr * 0.003))
    if len(d) < win * 8:
        # 너무 짧으면 시작·끝 5ms 사용
        edge = int(sr * 0.005)
        noise_seg = np.concatenate([d[:edge], d[-edge:]])
    else:
        # 전체 RMS 모니터링 → 가장 조용한 30ms 찾기
        sq = d ** 2
        cumsum = np.cumsum(sq)
        rms = np.sqrt((cumsum[win:] - cumsum[:-win]) / win)
        # 5% 분위수 이하 구간을 노이즈로
        q5 = np.quantile(rms, 0.05)
        quiet_idx = np.where(rms <= q5)[0]
        if len(quiet_idx) < 100:
            edge = int(sr * 0.005)
            noise_seg = np.concatenate([d[:edge], d[-edge:]])
        else:
            # 연속된 가장 긴 quiet 구간 추출
            noise_seg = d[quiet_idx[0]:quiet_idx[0] + min(int(sr * 0.03), len(quiet_idx))]
    # STFT magnitude 평균
    if len(noise_seg) < n_fft:
        # zero-pad
        noise_seg = np.pad(noise_seg, (0, n_fft - len(noise_seg) + 8), mode='constant')
    f, t, Zxx = signal.stft(noise_seg, fs=sr, nperseg=n_fft, noverlap=n_fft // 2)
    return np.mean(np.abs(Zxx), axis=1)  # shape: (n_fft//2 + 1,)


def spectral_subtract(d, sr, noise_mag, alpha=2.0, beta=0.04, n_fft=1024):
    """STFT 노이즈 차감.

    alpha: 노이즈 차감 강도 (보통 1.5~3)
    beta: residual floor (음악적 잡음 방지, 보통 0.02~0.06)
    """
    f, t, Zxx = signal.stft(d, fs=sr, nperseg=n_fft, noverlap=n_fft // 2)
    mag = np.abs(Zxx)
    phase = np.angle(Zxx)
    # 차감: max(mag - alpha*noise, beta*mag)
    noise_mag_b = noise_mag[:, np.newaxis]
    cleaned_mag = np.maximum(mag - alpha * noise_mag_b, beta * mag)
    cleaned_Zxx = cleaned_mag * np.exp(1j * phase)
    _, cleaned = signal.istft(cleaned_Zxx, fs=sr, nperseg=n_fft, noverlap=n_fft // 2)
    return cleaned[:len(d)]  # 길이 보정


def bandpass_filter(d, sr, low_hz=60, high_hz=14000):
    """저역 럼블·고역 hiss 제거."""
    nyq = sr / 2
    high_hz = min(high_hz, nyq * 0.95)
    sos = signal.butter(4, [low_hz / nyq, high_hz / nyq], btype='bandpass', output='sos')
    return signal.sosfiltfilt(sos, d)


def soft_noise_gate(d, sr, threshold=0.015, ratio=8.0, attack_ms=2, release_ms=20):
    """임계 이하 신호를 부드럽게 감쇠 (envelope follower 기반)."""
    # 빠른 envelope (RMS)
    win = max(1, int(sr * 0.001))
    sq = d ** 2
    cumsum = np.cumsum(sq)
    env = np.zeros_like(d)
    env[win:] = np.sqrt((cumsum[win:] - cumsum[:-win]) / win)
    env[:win] = env[win] if win < len(env) else 0
    # 부드러운 게인 곡선 (soft knee)
    db = 20 * np.log10(env + 1e-9)
    threshold_db = 20 * np.log10(threshold)
    knee_db = 6
    gain_db = np.zeros_like(db)
    below = db < (threshold_db - knee_db / 2)
    above = db > (threshold_db + knee_db / 2)
    knee = ~(below | above)
    # 임계 이상: 그대로
    gain_db[above] = 0
    # 임계 이하: -ratio 감쇠
    gain_db[below] = (db[below] - threshold_db) * (ratio - 1) / ratio
    # knee 영역: 부드럽게 보간
    if np.any(knee):
        kn_pos = (db[knee] - (threshold_db - knee_db / 2)) / knee_db  # 0~1
        gain_db[knee] = (db[knee] - threshold_db) * (ratio - 1) / ratio * (1 - kn_pos)
    # 너무 강한 감쇠 제한
    gain_db = np.clip(gain_db, -30, 0)
    # attack/release 평활화
    attack_n = max(1, int(sr * attack_ms / 1000))
    release_n = max(1, int(sr * release_ms / 1000))
    smoothed = np.zeros_like(gain_db)
    smoothed[0] = gain_db[0]
    for i in range(1, len(gain_db)):
        if gain_db[i] < smoothed[i - 1]:  # attack (감쇠 시작)
            alpha = 1.0 / attack_n
        else:  # release (감쇠 해제)
            alpha = 1.0 / release_n
        smoothed[i] = smoothed[i - 1] + alpha * (gain_db[i] - smoothed[i - 1])
    gain = 10 ** (smoothed / 20)
    return d * gain


def fade(d, sr, fade_ms=3):
    """짧은 fade in/out — 클릭/팝 방지"""
    n = max(1, int(sr * fade_ms / 1000))
    if len(d) < n * 2:
        return d
    fade_in = np.linspace(0, 1, n) ** 2
    fade_out = np.linspace(1, 0, n) ** 2
    d = d.copy()
    d[:n] *= fade_in
    d[-n:] *= fade_out
    return d


def normalize_peak(d, target_db=-3.0):
    """peak를 target_db로 정규화"""
    target = 10 ** (target_db / 20)
    peak = np.abs(d).max()
    if peak < 1e-9:
        return d
    return d * (target / peak)


def clean(d, sr):
    """전체 파이프라인."""
    # 1. Trim silence
    d = trim_silence(d, sr)
    # 너무 많이 잘리면 (50ms 미만) 트림 취소
    if len(d) < sr * 0.05:
        return None  # skip
    # 2. Noise profile 추정 (트림 전 원본에서 했다면 더 정확하지만 — 여기선 트림 후)
    noise_mag = estimate_noise_profile(d, sr)
    # 3. Spectral subtraction
    d = spectral_subtract(d, sr, noise_mag)
    # 4. Bandpass
    d = bandpass_filter(d, sr)
    # 5. Soft noise gate
    d = soft_noise_gate(d, sr)
    # 6. Fade
    d = fade(d, sr)
    # 7. Normalize
    d = normalize_peak(d, -3.0)
    return d


def process_file(in_path, out_path):
    sr, d = wavfile.read(in_path)
    if d.ndim > 1:
        d = d[:, 0]  # mono only
    d_f, dtype_str = to_float(d)
    cleaned = clean(d_f, sr)
    if cleaned is None:
        # skip — too short after trim. copy as-is
        wavfile.write(out_path, sr, d)
        return False
    out_int = to_pcm(cleaned, dtype_str if dtype_str != 'float' else np.float32)
    wavfile.write(out_path, sr, out_int)
    return True


def main(root):
    root = Path(root)
    n_done, n_skip = 0, 0
    for pack in sorted(root.iterdir(), key=lambda p: int(p.name) if p.name.isdigit() else 99):
        if not pack.is_dir():
            continue
        for wav in sorted(pack.glob('*.wav')):
            ok = process_file(str(wav), str(wav))
            if ok:
                n_done += 1
            else:
                n_skip += 1
    print(f"DONE: {n_done} processed, {n_skip} skipped (too short)")


if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else 'public/soundFiles'
    main(target)
