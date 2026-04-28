"""
타건음 v2 — '현장감' 처리.

v1 의 문제: 스펙트럴 차감이 musical noise(웅웅거림) 만듦 + 200~400Hz 머드 잔존.
v2 변경:
  1. Spectral subtraction → Wiener filter (musical noise 제거)
  2. 더 공격적인 HP (150Hz) — 마이크 근접효과 머드 제거
  3. 200Hz·320Hz 둘러 bell cut — 박스/룸 톤 제거
  4. 60Hz·120Hz·180Hz 노치 — 메인스 험 제거
  5. 4-6kHz presence boost — 클릭 임팩트 강화 (현장감)
  6. 더 빠른 fade·gate — '직접 타격' 느낌
  7. 처음 25ms transient 보존 (트림 더 보수적)
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


def trim_silence(d, sr, threshold_pct=0.06, edge_pad_ms=2):
    """더 보수적 — 시작 transient 손실 최소화."""
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
    pad = int(sr * edge_pad_ms / 1000)
    start = max(0, above[0] - pad * 2)  # 시작 패딩 더 — transient 보존
    end = min(len(d), above[-1] + win + pad)
    return d[start:end]


def estimate_noise_profile(d, sr, n_fft=1024):
    """가장 조용한 구간에서 노이즈 프로파일 추출."""
    win = max(1, int(sr * 0.003))
    if len(d) < win * 8:
        edge = int(sr * 0.005)
        noise_seg = np.concatenate([d[:edge], d[-edge:]])
    else:
        sq = d ** 2
        cumsum = np.cumsum(sq)
        rms = np.sqrt((cumsum[win:] - cumsum[:-win]) / win)
        q5 = np.quantile(rms, 0.05)
        quiet_idx = np.where(rms <= q5)[0]
        if len(quiet_idx) < 100:
            edge = int(sr * 0.005)
            noise_seg = np.concatenate([d[:edge], d[-edge:]])
        else:
            noise_seg = d[quiet_idx[0]:quiet_idx[0] + min(int(sr * 0.03), len(quiet_idx))]
    if len(noise_seg) < n_fft:
        noise_seg = np.pad(noise_seg, (0, n_fft - len(noise_seg) + 8), mode='constant')
    f, t, Zxx = signal.stft(noise_seg, fs=sr, nperseg=n_fft, noverlap=n_fft // 2)
    return np.mean(np.abs(Zxx) ** 2, axis=1) + 1e-12  # power spectrum


def wiener_denoise(d, sr, noise_psd, n_fft=1024):
    """Wiener filter — musical noise 없는 자연스러운 노이즈 감쇠.

    H(f) = SNR(f) / (SNR(f) + 1) — frequency-domain attenuation
    """
    f, t, Zxx = signal.stft(d, fs=sr, nperseg=n_fft, noverlap=n_fft // 2)
    sig_psd = np.abs(Zxx) ** 2
    noise_psd_b = noise_psd[:, np.newaxis]
    snr = np.maximum(sig_psd / noise_psd_b - 1, 0)  # a priori SNR
    # Smoothing — 시간축 평활화 (musical noise 추가 방지)
    snr_smooth = np.zeros_like(snr)
    snr_smooth[:, 0] = snr[:, 0]
    smooth_alpha = 0.7  # 시간 평활화 강도
    for i in range(1, snr.shape[1]):
        snr_smooth[:, i] = smooth_alpha * snr_smooth[:, i - 1] + (1 - smooth_alpha) * snr[:, i]
    H = snr_smooth / (snr_smooth + 1)
    # Floor — 너무 강한 차감 방지 (자연스러움 유지)
    H = np.maximum(H, 0.15)
    cleaned_Zxx = Zxx * H
    _, cleaned = signal.istft(cleaned_Zxx, fs=sr, nperseg=n_fft, noverlap=n_fft // 2)
    return cleaned[:len(d)]


def design_eq(sr):
    """현장감 EQ 체인 설계 — 한 번 만들고 재사용."""
    nyq = sr / 2
    sos_chain = []

    # 1. HP 150Hz — 마이크 근접효과 + 럼블 제거
    sos_chain.append(signal.butter(4, 150 / nyq, btype='highpass', output='sos'))

    # 2. Notch at 60Hz, 120Hz, 180Hz — 메인스 험
    for fc in [60, 120, 180]:
        if fc < nyq:
            b, a = signal.iirnotch(fc / nyq, Q=20)
            sos_chain.append(signal.tf2sos(b, a))

    # 3. Bell cut at 220Hz — 박스/룸 톤 ("웅웅" 영역)
    b, a = signal.iirpeak(220 / nyq, Q=2.0)  # peak 필터 게인 조정 위해 직접 계수 작성
    # iirpeak는 +6dB 부스트가 기본 — cut으로 변환
    # 직접 IIR coefficient 만들기 — bell cut 4dB
    f0 = 220 / nyq
    Q = 2.0
    gain_db = -4.0
    A = 10 ** (gain_db / 40)
    w0 = np.pi * f0
    cw = np.cos(w0); sw = np.sin(w0)
    alpha = sw / (2 * Q)
    b0 = 1 + alpha * A; b1 = -2 * cw; b2 = 1 - alpha * A
    a0 = 1 + alpha / A; a1 = -2 * cw; a2 = 1 - alpha / A
    b_coef = np.array([b0, b1, b2]) / a0
    a_coef = np.array([1.0, a1 / a0, a2 / a0])
    sos_chain.append(signal.tf2sos(b_coef, a_coef))

    # 4. Bell cut at 350Hz — 머드 영역
    f0 = 350 / nyq; Q = 1.5; gain_db = -3.0
    A = 10 ** (gain_db / 40); w0 = np.pi * f0
    cw = np.cos(w0); sw = np.sin(w0); alpha = sw / (2 * Q)
    b0 = 1 + alpha * A; b1 = -2 * cw; b2 = 1 - alpha * A
    a0 = 1 + alpha / A; a1 = -2 * cw; a2 = 1 - alpha / A
    sos_chain.append(signal.tf2sos(np.array([b0, b1, b2]) / a0,
                                    np.array([1.0, a1 / a0, a2 / a0])))

    # 5. Bell boost at 5kHz — 클릭 presence/현장감
    if 5000 < nyq:
        f0 = 5000 / nyq; Q = 1.0; gain_db = +3.5
        A = 10 ** (gain_db / 40); w0 = np.pi * f0
        cw = np.cos(w0); sw = np.sin(w0); alpha = sw / (2 * Q)
        b0 = 1 + alpha * A; b1 = -2 * cw; b2 = 1 - alpha * A
        a0 = 1 + alpha / A; a1 = -2 * cw; a2 = 1 - alpha / A
        sos_chain.append(signal.tf2sos(np.array([b0, b1, b2]) / a0,
                                        np.array([1.0, a1 / a0, a2 / a0])))

    # 6. LP shelf at 14kHz — hiss 제거 (자연스럽게)
    if 14000 < nyq:
        sos_chain.append(signal.butter(2, 14000 / nyq, btype='lowpass', output='sos'))

    return np.vstack(sos_chain)


def apply_eq(d, sos):
    return signal.sosfiltfilt(sos, d)


def fast_gate(d, sr, threshold_pct=0.04, attack_ms=0.5, release_ms=12):
    """더 빠른 게이트 — 직접 타격 느낌."""
    win = max(1, int(sr * 0.001))
    sq = d ** 2
    cumsum = np.cumsum(sq)
    env = np.zeros_like(d)
    env[win:] = np.sqrt((cumsum[win:] - cumsum[:-win]) / win)
    env[:win] = env[win] if win < len(env) else 0
    threshold = env.max() * threshold_pct
    target_gain = np.where(env > threshold, 1.0, 0.0)
    # smooth
    attack_n = max(1, int(sr * attack_ms / 1000))
    release_n = max(1, int(sr * release_ms / 1000))
    smoothed = np.zeros_like(target_gain)
    smoothed[0] = target_gain[0]
    for i in range(1, len(target_gain)):
        if target_gain[i] < smoothed[i - 1]:
            alpha = 1.0 / release_n  # 느리게 닫기
        else:
            alpha = 1.0 / attack_n  # 빠르게 열기
        smoothed[i] = smoothed[i - 1] + alpha * (target_gain[i] - smoothed[i - 1])
    smoothed = np.clip(smoothed, 0.05, 1.0)  # 완전 무음 방지 (자연스러움)
    return d * smoothed


def fade(d, sr, fade_in_ms=1, fade_out_ms=4):
    """짧은 fade — 시작 transient 보존, 끝은 부드럽게."""
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


def clean_v2(d, sr, eq_sos):
    d = trim_silence(d, sr)
    if len(d) < sr * 0.05:
        return None
    noise_psd = estimate_noise_profile(d, sr)
    d = wiener_denoise(d, sr, noise_psd)
    d = apply_eq(d, eq_sos)
    d = fast_gate(d, sr)
    d = fade(d, sr)
    d = normalize_peak(d, -3.0)
    return d


def process_file(in_path, out_path, eq_sos):
    sr, d = wavfile.read(in_path)
    if d.ndim > 1:
        d = d[:, 0]
    d_f, dtype_str = to_float(d)
    cleaned = clean_v2(d_f, sr, eq_sos)
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
        print(f"ERROR: {src_root} 없음. 백업이 있어야 함.")
        sys.exit(1)
    # EQ 한 번만 설계 (모든 파일이 같은 sr이라 가정 — 첫 파일에서 sr 가져옴)
    eq_sos = None
    n_done, n_skip = 0, 0
    for pack in sorted(src_root.iterdir(), key=lambda p: int(p.name) if p.name.isdigit() else 99):
        if not pack.is_dir():
            continue
        for wav in sorted(pack.glob('*.wav')):
            if eq_sos is None:
                sr_check, _ = wavfile.read(wav)
                eq_sos = design_eq(sr_check)
                print(f"EQ designed for sr={sr_check}Hz, {len(eq_sos)} biquad sections")
            rel = wav.relative_to(src_root)
            dst = dst_root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            ok = process_file(str(wav), str(dst), eq_sos)
            if ok:
                n_done += 1
            else:
                n_skip += 1
    print(f"DONE v2: {n_done} processed, {n_skip} skipped")


if __name__ == '__main__':
    src = sys.argv[1] if len(sys.argv) > 1 else 'public/soundFiles_original'
    dst = sys.argv[2] if len(sys.argv) > 2 else 'public/soundFiles'
    main(src, dst)
