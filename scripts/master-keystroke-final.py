"""
타건음 v4 — 마스터링 + 라우드니스 정규화 + "현장감" 처리.

목표:
  1. 13팩 전체 평균 음량 동일 (RMS 기반, peak 가 아님)
  2. 녹음된 사운드 → "실시간으로 듣는" 느낌
  3. 룸톤·배경잡음 깔끔히 제거 (가상 사운드 느낌 제거)

처리 파이프라인:
  Pass 1 (각 파일):
    a. Trim 시작·끝 무음 (공격적 — 실시간 직접 타격 느낌)
    b. Spectral noise reduction — 룸톤 / 일정한 노이즈 floor 제거
    c. "Live" EQ:
       - HP 100Hz   (저역 mud 제거)
       - Bell -3dB at 280Hz Q=2  (룸 리조넌스)
       - Bell -2dB at 450Hz Q=1.5 (boxy mud)
       - Shelf +2dB at 5kHz (직접성·presence)
       - LP 14kHz shelf (hiss 통제)
    d. Aggressive gate — quiet portions 무음화 (잔향 제거)
    e. Fade in 0.5ms / Fade out 5ms
    f. Capture RMS for normalization

  Pass 2 (라우드니스 매칭):
    - 모든 130 파일 RMS 평균 계산
    - 각 파일을 target RMS 로 정규화 (보수적 - 너무 차이 큰 건 부분 보정만)
    - Soft limiter — peak -1dBFS

결과: 모든 팩이 같은 perceived loudness, 깔끔한 배경, 직접적인 "현장 타격" 느낌.
"""
import sys
import json
import numpy as np
import soundfile as sf
import scipy.io.wavfile as wavfile
from scipy import signal
from pathlib import Path


# ─────────────────────────────────────────────────────────
# 1. 기본 유틸
# ─────────────────────────────────────────────────────────
def to_float(d):
    if np.issubdtype(d.dtype, np.floating):
        return d.astype(np.float64)
    info = np.iinfo(d.dtype)
    return d.astype(np.float64) / max(abs(info.min), info.max)


# ─────────────────────────────────────────────────────────
# 2. 공격적 트림 (실시간 타격 느낌)
# ─────────────────────────────────────────────────────────
def aggressive_trim(d, sr, threshold_pct=0.05, head_pad_ms=1, tail_pad_ms=3):
    """시작 1ms, 끝 3ms만 패드 — 매우 짧고 직접적."""
    win = max(1, int(sr * 0.002))
    if len(d) < win * 4:
        return d
    sq = d ** 2
    cumsum = np.cumsum(sq)
    rms = np.sqrt((cumsum[win:] - cumsum[:-win]) / win)
    threshold = rms.max() * threshold_pct
    above = np.where(rms > threshold)[0]
    if len(above) == 0:
        return d
    head_pad = int(sr * head_pad_ms / 1000)
    tail_pad = int(sr * tail_pad_ms / 1000)
    start = max(0, above[0] - head_pad)
    end = min(len(d), above[-1] + win + tail_pad)
    return d[start:end]


# ─────────────────────────────────────────────────────────
# 3. Spectral noise reduction (룸톤 제거)
# ─────────────────────────────────────────────────────────
def estimate_noise_floor(d, sr, n_fft=1024):
    """파일에서 가장 조용한 구간을 노이즈로 사용."""
    win = max(1, int(sr * 0.003))
    if len(d) < win * 8:
        # 매우 짧으면 시작 5ms
        edge = int(sr * 0.005)
        seg = d[:edge] if len(d) > edge else d
        if len(seg) < n_fft:
            seg = np.pad(seg, (0, n_fft - len(seg) + 8))
        f, t, Zxx = signal.stft(seg, fs=sr, nperseg=n_fft, noverlap=n_fft // 2)
        return np.mean(np.abs(Zxx) ** 2, axis=1) + 1e-12
    sq = d ** 2
    cumsum = np.cumsum(sq)
    rms = np.sqrt((cumsum[win:] - cumsum[:-win]) / win)
    q5 = np.quantile(rms, 0.05)
    quiet_idx = np.where(rms <= q5)[0]
    if len(quiet_idx) < 100:
        edge = int(sr * 0.005)
        seg = d[:edge]
    else:
        seg = d[quiet_idx[0]:quiet_idx[0] + min(int(sr * 0.03), len(quiet_idx))]
    if len(seg) < n_fft:
        seg = np.pad(seg, (0, n_fft - len(seg) + 8))
    f, t, Zxx = signal.stft(seg, fs=sr, nperseg=n_fft, noverlap=n_fft // 2)
    return np.mean(np.abs(Zxx) ** 2, axis=1) + 1e-12


def wiener_denoise(d, sr, noise_psd, n_fft=1024, floor=0.10):
    """Wiener filter — 룸톤 차감, musical noise 없음."""
    f, t, Zxx = signal.stft(d, fs=sr, nperseg=n_fft, noverlap=n_fft // 2)
    sig_psd = np.abs(Zxx) ** 2
    snr = np.maximum(sig_psd / noise_psd[:, np.newaxis] - 1, 0)
    # Time smoothing for natural sound
    snr_smooth = np.zeros_like(snr)
    snr_smooth[:, 0] = snr[:, 0]
    for i in range(1, snr.shape[1]):
        snr_smooth[:, i] = 0.7 * snr_smooth[:, i - 1] + 0.3 * snr[:, i]
    H = snr_smooth / (snr_smooth + 1)
    H = np.maximum(H, floor)
    cleaned_Zxx = Zxx * H
    _, cleaned = signal.istft(cleaned_Zxx, fs=sr, nperseg=n_fft, noverlap=n_fft // 2)
    return cleaned[:len(d)]


# ─────────────────────────────────────────────────────────
# 4. "Live" EQ — 현장감 EQ
# ─────────────────────────────────────────────────────────
def design_live_eq(sr):
    nyq = sr / 2
    chain = []

    # HP at 100Hz — 저역 mud + DC offset 제거
    chain.append(signal.butter(2, 100 / nyq, btype='highpass', output='sos'))

    # Bell cut at 280Hz, -3dB, Q=2 — 룸 리조넌스 제거
    def make_bell(f0, Q, gain_db, sr):
        nyq = sr / 2
        f_norm = f0 / nyq
        A = 10 ** (gain_db / 40)
        w0 = np.pi * f_norm
        cw = np.cos(w0); sw = np.sin(w0)
        alpha = sw / (2 * Q)
        b0 = 1 + alpha * A; b1 = -2 * cw; b2 = 1 - alpha * A
        a0 = 1 + alpha / A; a1 = -2 * cw; a2 = 1 - alpha / A
        b = np.array([b0, b1, b2]) / a0
        a = np.array([1.0, a1 / a0, a2 / a0])
        return signal.tf2sos(b, a)

    chain.append(make_bell(280, 2.0, -3.0, sr))   # 룸 리조넌스
    chain.append(make_bell(450, 1.5, -2.0, sr))   # boxy mud
    if 5000 < nyq:
        chain.append(make_bell(5000, 0.9, +2.0, sr))  # presence

    # LP shelf at 14kHz (hiss control)
    if 14000 < nyq:
        chain.append(signal.butter(2, 14000 / nyq, btype='lowpass', output='sos'))

    return np.vstack(chain)


def apply_eq(d, sos):
    return signal.sosfiltfilt(sos, d)


# ─────────────────────────────────────────────────────────
# 5. Aggressive gate — 잔향 제거
# ─────────────────────────────────────────────────────────
def aggressive_gate(d, sr, threshold_pct=0.05, attenuation_db=-40, attack_ms=0.5, release_ms=15):
    """임계 이하 -40dB 감쇠 — 룸톤/잔향 사라짐."""
    win = max(1, int(sr * 0.0015))
    sq = d ** 2
    cumsum = np.cumsum(sq)
    env = np.zeros_like(d)
    env[win:] = np.sqrt((cumsum[win:] - cumsum[:-win]) / win)
    env[:win] = env[win] if win < len(env) else 0
    threshold = env.max() * threshold_pct
    target_lin = 10 ** (attenuation_db / 20)
    target_gain = np.where(env > threshold, 1.0, target_lin)
    attack_n = max(1, int(sr * attack_ms / 1000))
    release_n = max(1, int(sr * release_ms / 1000))
    smoothed = np.zeros_like(target_gain)
    smoothed[0] = target_gain[0]
    for i in range(1, len(target_gain)):
        if target_gain[i] < smoothed[i - 1]:
            alpha = 1.0 / release_n
        else:
            alpha = 1.0 / attack_n
        smoothed[i] = smoothed[i - 1] + alpha * (target_gain[i] - smoothed[i - 1])
    return d * smoothed


# ─────────────────────────────────────────────────────────
# 6. Fade
# ─────────────────────────────────────────────────────────
def fade(d, sr, fade_in_ms=0.5, fade_out_ms=4):
    n_in = max(1, int(sr * fade_in_ms / 1000))
    n_out = max(1, int(sr * fade_out_ms / 1000))
    if len(d) < (n_in + n_out) * 2:
        return d
    d = d.copy()
    d[:n_in] *= np.linspace(0, 1, n_in) ** 1.2
    d[-n_out:] *= np.linspace(1, 0, n_out) ** 2
    return d


# ─────────────────────────────────────────────────────────
# 7. RMS measurement (가장 큰 부분 기준 — silence 제외)
# ─────────────────────────────────────────────────────────
def measure_active_rms(d, sr):
    """전체가 아닌 '활성 구간'(상위 60% 영역)의 RMS — 진짜 perceived loudness."""
    if len(d) < int(sr * 0.01):
        return 1e-9
    win = max(1, int(sr * 0.003))
    sq = d ** 2
    cumsum = np.cumsum(sq)
    rms = np.sqrt((cumsum[win:] - cumsum[:-win]) / win)
    # Top 40% RMS samples 사용 (충격 + 직후 body)
    threshold = np.quantile(rms, 0.60)
    active = rms[rms >= threshold]
    if len(active) == 0:
        return np.sqrt(np.mean(d ** 2))
    return np.sqrt(np.mean(active ** 2))


# ─────────────────────────────────────────────────────────
# 8. Soft limiter
# ─────────────────────────────────────────────────────────
def soft_limit(d, ceiling_db=-1.0):
    """Tanh-style soft limiter — clip 없이 ceiling 보장."""
    ceiling = 10 ** (ceiling_db / 20)
    peak = np.abs(d).max()
    if peak <= ceiling:
        return d
    # 피크가 너무 높으면 미리 0.95로 축소 후 tanh 적용
    pre_scale = ceiling * 1.5 / peak
    scaled = d * pre_scale
    limited = ceiling * np.tanh(scaled / ceiling)
    return limited


# ─────────────────────────────────────────────────────────
# 9. Per-file processing (Pass 1)
# ─────────────────────────────────────────────────────────
def process_pass1(in_path, out_path, eq_sos):
    """파일 처리하고 active RMS 반환."""
    sr, d = wavfile.read(in_path)
    if d.ndim > 1:
        d = d[:, 0]
    d = to_float(d)

    # 1. Aggressive trim
    d = aggressive_trim(d, sr)
    if len(d) < int(sr * 0.02):
        # 너무 짧음 — skip
        return None

    # 2. Spectral noise reduction
    noise_psd = estimate_noise_floor(d, sr)
    d = wiener_denoise(d, sr, noise_psd)

    # 3. Live EQ
    d = apply_eq(d, eq_sos)

    # 4. Aggressive gate (잔향 제거)
    d = aggressive_gate(d, sr)

    # 5. Fade
    d = fade(d, sr)

    # 6. 임시 정규화 to -6dB peak (Pass 2 에서 다시 조정)
    peak = np.abs(d).max()
    if peak > 1e-9:
        d = d * (10 ** (-6 / 20)) / peak

    # 임시 저장 + RMS 측정
    rms = measure_active_rms(d, sr)
    wavfile.write(out_path, sr, d.astype(np.float32))
    return rms


# ─────────────────────────────────────────────────────────
# 10. Loudness matching (Pass 2)
# ─────────────────────────────────────────────────────────
def process_pass2(file_paths, rms_values, target_rms_db=-20.0):
    """모든 파일 RMS를 target에 맞춰 정규화 + soft limit."""
    target_rms = 10 ** (target_rms_db / 20)
    for path, rms in zip(file_paths, rms_values):
        if rms is None or rms < 1e-9:
            continue
        sr, d = wavfile.read(path)
        if d.ndim > 1:
            d = d[:, 0]
        d = to_float(d)
        # Gain to match target RMS
        gain = target_rms / rms
        # 너무 강한 boost는 제한 (8x = +18dB max)
        gain = min(gain, 8.0)
        d = d * gain
        # Soft limit at -1dBFS
        d = soft_limit(d, ceiling_db=-1.0)
        wavfile.write(path, sr, d.astype(np.float32))


# ─────────────────────────────────────────────────────────
# 11. Main
# ─────────────────────────────────────────────────────────
def main(root='public/soundFiles'):
    root = Path(root)
    if not root.exists():
        print(f"ERROR: {root} 없음")
        return

    # EQ 한 번만 설계 (sr=48000 가정)
    eq_sos = design_live_eq(48000)

    # Pass 1: 각 파일 처리 + RMS 측정
    print("=" * 65)
    print("Pass 1: 처리 + 정리 + RMS 측정")
    print("=" * 65)
    all_paths = []
    all_rms = []
    for pack in sorted(root.iterdir(), key=lambda p: int(p.name) if p.name.isdigit() else 99):
        if not pack.is_dir():
            continue
        pack_paths = []
        pack_rms = []
        for wav in sorted(pack.glob('*.wav')):
            rms = process_pass1(str(wav), str(wav), eq_sos)
            pack_paths.append(str(wav))
            pack_rms.append(rms)
            all_paths.append(str(wav))
            all_rms.append(rms)
        valid_rms = [r for r in pack_rms if r is not None]
        if valid_rms:
            avg = np.mean(valid_rms)
            avg_db = 20 * np.log10(avg + 1e-9)
            print(f"  Pack {pack.name:>2s}: {len(valid_rms)}/10  active RMS avg = {avg_db:+5.1f}dB")

    # 전체 평균 RMS 계산
    valid_all = [r for r in all_rms if r is not None]
    if valid_all:
        global_avg_rms = np.mean(valid_all)
        global_avg_db = 20 * np.log10(global_avg_rms + 1e-9)
        print(f"\n  글로벌 평균 active RMS: {global_avg_db:+5.1f}dB ({len(valid_all)} 파일)")

    # Pass 2: 모든 파일을 같은 target RMS 로 정규화
    target_db = -18.0  # -18dBFS active RMS — 충분히 시끄럽지만 헤드룸 있음
    print(f"\n" + "=" * 65)
    print(f"Pass 2: 모든 파일 → target RMS {target_db:+.1f}dB 로 정규화")
    print("=" * 65)
    process_pass2(all_paths, all_rms, target_rms_db=target_db)

    # 검증
    print("\n검증 (각 팩 최종 RMS):")
    for pack in sorted(root.iterdir(), key=lambda p: int(p.name) if p.name.isdigit() else 99):
        if not pack.is_dir():
            continue
        rms_list = []
        peak_list = []
        for wav in sorted(pack.glob('*.wav')):
            sr, d = wavfile.read(wav)
            if d.ndim > 1: d = d[:, 0]
            d = to_float(d)
            rms_list.append(measure_active_rms(d, sr))
            peak_list.append(np.abs(d).max())
        if rms_list:
            avg_rms_db = 20 * np.log10(np.mean(rms_list) + 1e-9)
            avg_peak_db = 20 * np.log10(np.mean(peak_list) + 1e-9)
            print(f"  Pack {pack.name:>2s}: RMS {avg_rms_db:+5.1f}dB | peak {avg_peak_db:+5.1f}dB")


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'public/soundFiles')
