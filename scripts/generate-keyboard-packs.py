"""
13개 키보드 사운드 팩 합성 — 진짜 메커니컬 키보드 같은 사운드.

각 팩은 서로 다른 스위치 특성:
  1. Cherry MX Red       — Linear, 부드럽고 가벼움
  2. Cherry MX Brown     — Tactile, 살짝 bump
  3. Cherry MX Blue      — Clicky, 샤프한 click
  4. Cherry MX Black     — Heavy linear, 깊은 body
  5. Topre 45g           — Soft thock, 따뜻함
  6. Buckling Spring     — Loud mechanical (IBM Model M 느낌)
  7. Alps White          — Bright snappy
  8. Kailh Box White     — Clicky, MX Blue 계열
  9. Gateron Yellow      — Smooth deep linear
 10. Holy Panda          — Tactile + crispy clack
 11. Silent MX           — Dampened, 매우 부드러움
 12. Optical Linear      — Clean fast attack
 13. Typewriter          — Vintage mechanical (clackety)

각 팩에 10개 variation (.wav). Variation은 force / position / micro-randomization.
"""
import os
import sys
import numpy as np
import scipy.io.wavfile as wavfile
from scipy import signal
from pathlib import Path


SR = 48000  # 48kHz
DURATION_MS = 180  # 각 keystroke ~180ms (자연스러운 길이)


def make_noise_burst(length, sr, freq_low, freq_high, decay_factor=0.10):
    """대역 필터링된 노이즈 burst — 메커니컬 click의 핵심.

    decay_factor: 작을수록 빠른 감쇠 (0.05 = 매우 빠른 click, 0.3 = 부드러운 burst)
    """
    n = int(length * sr / 1000)
    if n < 8:
        n = 8
    raw = np.random.randn(n)
    # Exponential decay envelope
    env = np.exp(-np.arange(n) / (n * decay_factor))
    raw *= env
    # Bandpass filter
    nyq = sr / 2
    low = max(20, freq_low) / nyq
    high = min(freq_high, nyq * 0.95) / nyq
    sos = signal.butter(4, [low, high], btype='bandpass', output='sos')
    return signal.sosfiltfilt(sos, raw)


def make_tone_burst(length, sr, freq, freq_drop_to=None, decay_ms=None, wave='sine'):
    """짧은 톤 burst — body resonance / thump.

    freq_drop_to: 시작 주파수에서 끝 주파수로 빠르게 drop (impact 느낌)
    """
    n = int(length * sr / 1000)
    if n < 8:
        n = 8
    t = np.arange(n) / sr
    if freq_drop_to is None:
        freq_drop_to = freq
    # Frequency envelope (지수적 drop)
    if decay_ms is None:
        decay_ms = length * 0.4
    decay_n = max(1, int(decay_ms * sr / 1000))
    freq_env = freq_drop_to + (freq - freq_drop_to) * np.exp(-np.arange(n) / decay_n)
    # Phase 누적
    phase = 2 * np.pi * np.cumsum(freq_env) / sr
    if wave == 'sine':
        sig = np.sin(phase)
    elif wave == 'triangle':
        sig = signal.sawtooth(phase, 0.5)
    elif wave == 'saw':
        sig = signal.sawtooth(phase)
    else:
        sig = np.sin(phase)
    # Amplitude envelope — 빠른 attack + 자연스러운 decay
    amp_attack_n = max(1, int(0.001 * sr))  # 1ms attack
    amp_env = np.ones(n)
    amp_env[:amp_attack_n] = np.linspace(0, 1, amp_attack_n) ** 2
    amp_env[amp_attack_n:] = np.exp(-np.arange(n - amp_attack_n) / (n * 0.18))
    return sig * amp_env


def make_pink_tail(length_ms, sr, lp_freq=1500):
    """짧은 pink noise tail — 자연스러운 마감."""
    n = int(length_ms * sr / 1000)
    if n < 16:
        return np.zeros(n)
    raw = np.random.randn(n)
    # Pink noise (1/f) approximation
    b0 = b1 = b2 = b3 = 0
    for i in range(n):
        w = raw[i]
        b0 = 0.99 * b0 + w * 0.05
        b1 = 0.96 * b1 + w * 0.10
        b2 = 0.86 * b2 + w * 0.30
        b3 = 0.55 * b3 + w * 0.53
        raw[i] = (b0 + b1 + b2 + b3) * 0.15
    nyq = sr / 2
    sos = signal.butter(2, lp_freq / nyq, btype='lowpass', output='sos')
    raw = signal.sosfiltfilt(sos, raw)
    # Decay envelope
    env = np.exp(-np.arange(n) / (n * 0.25))
    return raw * env


def synthesize_keystroke(preset, seed=None):
    """preset dict 기반으로 keystroke 합성.

    preset 키:
      click_freq_low, click_freq_high, click_amp, click_decay
      body_freq, body_drop_ratio, body_amp, body_decay_ms, body_wave
      thump_freq, thump_amp, thump_decay_ms
      tail_amp, tail_lp
      release_amp (0이면 release 없음)
      release_delay_ms
      total_ms
      randomize (0~1)
    """
    if seed is not None:
        np.random.seed(seed)
    rnd = lambda spread: 1 + (np.random.rand() * 2 - 1) * spread
    R = preset.get('randomize', 0.08)

    total_ms = preset['total_ms']
    n_total = int(total_ms * SR / 1000)
    out = np.zeros(n_total + int(0.05 * SR))  # 50ms 여유

    # 1. Click (high transient)
    click_low = preset['click_freq_low'] * rnd(R * 0.5)
    click_high = preset['click_freq_high'] * rnd(R * 0.3)
    click_decay = preset['click_decay'] * rnd(R)
    click_len = preset.get('click_len_ms', 16) * rnd(R * 0.4)
    click = make_noise_burst(click_len, SR, click_low, click_high, click_decay)
    click *= preset['click_amp'] * rnd(R)
    out[:len(click)] += click

    # 2. Body resonance
    body_freq = preset['body_freq'] * rnd(R * 0.6)
    body_drop = body_freq * preset.get('body_drop_ratio', 0.7)
    body_decay = preset.get('body_decay_ms', 50) * rnd(R * 0.4)
    body_len = preset.get('body_len_ms', 60) * rnd(R * 0.3)
    body = make_tone_burst(
        body_len, SR, body_freq, body_drop,
        decay_ms=body_decay,
        wave=preset.get('body_wave', 'triangle')
    )
    body *= preset['body_amp'] * rnd(R)
    body_offset = max(0, int(preset.get('body_delay_ms', 0) * SR / 1000))
    end = min(len(out), body_offset + len(body))
    out[body_offset:end] += body[:end - body_offset]

    # 3. Thump (low impact)
    if preset.get('thump_amp', 0) > 0:
        thump_freq = preset['thump_freq'] * rnd(R * 0.4)
        thump_drop = thump_freq * 0.6
        thump_len = preset.get('thump_len_ms', 50)
        thump = make_tone_burst(
            thump_len, SR, thump_freq * 1.3, thump_drop,
            decay_ms=preset.get('thump_decay_ms', 30),
            wave='sine'
        )
        thump *= preset['thump_amp'] * rnd(R * 0.6)
        thump_offset = max(0, int(preset.get('thump_delay_ms', 1) * SR / 1000))
        end = min(len(out), thump_offset + len(thump))
        out[thump_offset:end] += thump[:end - thump_offset]

    # 4. Tail (pink noise)
    if preset.get('tail_amp', 0) > 0:
        tail = make_pink_tail(preset.get('tail_len_ms', 40), SR, preset.get('tail_lp', 1500))
        tail *= preset['tail_amp'] * rnd(R * 0.5)
        tail_offset = max(0, int(preset.get('tail_delay_ms', 5) * SR / 1000))
        end = min(len(out), tail_offset + len(tail))
        out[tail_offset:end] += tail[:end - tail_offset]

    # 5. Release click (떼는 소리)
    if preset.get('release_amp', 0) > 0:
        rel_delay = preset.get('release_delay_ms', 60) * rnd(R * 0.3)
        rel_len = preset.get('release_len_ms', 10)
        rel_decay = preset.get('release_decay', 0.1)
        rel_low = preset.get('release_freq_low', 1500)
        rel_high = preset.get('release_freq_high', 7000)
        rel = make_noise_burst(rel_len, SR, rel_low, rel_high, rel_decay)
        rel *= preset['release_amp'] * rnd(R)
        rel_offset = int(rel_delay * SR / 1000)
        end = min(len(out), rel_offset + len(rel))
        out[rel_offset:end] += rel[:end - rel_offset]

    # 6. 전체 길이 자르기 + 정규화 + 짧은 fade
    out = out[:n_total]
    # 짧은 fade out (3ms)
    fade_n = int(0.003 * SR)
    if len(out) > fade_n * 2:
        out[-fade_n:] *= np.linspace(1, 0, fade_n) ** 2
    # Peak normalize to -3dB
    peak = np.abs(out).max()
    if peak > 1e-9:
        out = out * (10 ** (-3 / 20)) / peak
    return out


# ─────────────────────────────────────────────────────────────────
# 13개 프리셋 정의
# ─────────────────────────────────────────────────────────────────
PRESETS = [
    # 1. Cherry MX Red — Linear, smooth, light
    {
        'name': 'mx-red',
        'click_freq_low': 2200, 'click_freq_high': 5500, 'click_amp': 0.45,
        'click_decay': 0.10, 'click_len_ms': 14,
        'body_freq': 380, 'body_drop_ratio': 0.65, 'body_amp': 0.20,
        'body_decay_ms': 45, 'body_len_ms': 55, 'body_wave': 'triangle', 'body_delay_ms': 1,
        'thump_freq': 95, 'thump_amp': 0.28, 'thump_len_ms': 50, 'thump_decay_ms': 28,
        'tail_amp': 0.10, 'tail_lp': 1800, 'tail_len_ms': 40,
        'release_amp': 0.18, 'release_delay_ms': 65, 'release_freq_low': 1800, 'release_freq_high': 5000,
        'total_ms': 160, 'randomize': 0.10,
    },
    # 2. Cherry MX Brown — Tactile bump
    {
        'name': 'mx-brown',
        'click_freq_low': 2500, 'click_freq_high': 6500, 'click_amp': 0.50,
        'click_decay': 0.09, 'click_len_ms': 15,
        'body_freq': 420, 'body_drop_ratio': 0.60, 'body_amp': 0.25,
        'body_decay_ms': 50, 'body_len_ms': 60, 'body_wave': 'triangle',
        'thump_freq': 100, 'thump_amp': 0.30, 'thump_len_ms': 55, 'thump_decay_ms': 30,
        'tail_amp': 0.12, 'tail_lp': 2000, 'tail_len_ms': 45,
        'release_amp': 0.22, 'release_delay_ms': 60, 'release_freq_low': 2000, 'release_freq_high': 5500,
        'total_ms': 170, 'randomize': 0.10,
    },
    # 3. Cherry MX Blue — Clicky sharp
    {
        'name': 'mx-blue',
        'click_freq_low': 3500, 'click_freq_high': 9000, 'click_amp': 0.65,
        'click_decay': 0.07, 'click_len_ms': 12,
        'body_freq': 480, 'body_drop_ratio': 0.55, 'body_amp': 0.30,
        'body_decay_ms': 55, 'body_len_ms': 70, 'body_wave': 'triangle',
        'thump_freq': 105, 'thump_amp': 0.32, 'thump_len_ms': 50, 'thump_decay_ms': 32,
        'tail_amp': 0.10, 'tail_lp': 2200, 'tail_len_ms': 50,
        'release_amp': 0.40, 'release_delay_ms': 55, 'release_freq_low': 2500, 'release_freq_high': 7500,
        'release_decay': 0.06,
        'total_ms': 180, 'randomize': 0.09,
    },
    # 4. Cherry MX Black — Heavy linear
    {
        'name': 'mx-black',
        'click_freq_low': 1800, 'click_freq_high': 4500, 'click_amp': 0.42,
        'click_decay': 0.12, 'click_len_ms': 18,
        'body_freq': 320, 'body_drop_ratio': 0.62, 'body_amp': 0.30,
        'body_decay_ms': 60, 'body_len_ms': 75, 'body_wave': 'triangle',
        'thump_freq': 80, 'thump_amp': 0.42, 'thump_len_ms': 60, 'thump_decay_ms': 40,
        'tail_amp': 0.14, 'tail_lp': 1500, 'tail_len_ms': 50,
        'release_amp': 0.18, 'release_delay_ms': 70, 'release_freq_low': 1500, 'release_freq_high': 4500,
        'total_ms': 180, 'randomize': 0.10,
    },
    # 5. Topre 45g — Soft thock
    {
        'name': 'topre',
        'click_freq_low': 1500, 'click_freq_high': 3800, 'click_amp': 0.30,
        'click_decay': 0.15, 'click_len_ms': 20,
        'body_freq': 280, 'body_drop_ratio': 0.55, 'body_amp': 0.40,
        'body_decay_ms': 70, 'body_len_ms': 90, 'body_wave': 'sine',
        'thump_freq': 90, 'thump_amp': 0.45, 'thump_len_ms': 70, 'thump_decay_ms': 50,
        'tail_amp': 0.10, 'tail_lp': 1200, 'tail_len_ms': 45,
        'release_amp': 0.10, 'release_delay_ms': 75, 'release_freq_low': 1200, 'release_freq_high': 3500,
        'total_ms': 180, 'randomize': 0.08,
    },
    # 6. Buckling Spring (IBM Model M)
    {
        'name': 'buckling',
        'click_freq_low': 4500, 'click_freq_high': 11000, 'click_amp': 0.85,
        'click_decay': 0.05, 'click_len_ms': 10,
        'body_freq': 600, 'body_drop_ratio': 0.50, 'body_amp': 0.35,
        'body_decay_ms': 50, 'body_len_ms': 80, 'body_wave': 'triangle',
        'thump_freq': 120, 'thump_amp': 0.40, 'thump_len_ms': 50, 'thump_decay_ms': 35,
        'tail_amp': 0.12, 'tail_lp': 2500, 'tail_len_ms': 60,
        'release_amp': 0.55, 'release_delay_ms': 50, 'release_freq_low': 3000, 'release_freq_high': 9000,
        'release_decay': 0.05,
        'total_ms': 180, 'randomize': 0.08,
    },
    # 7. Alps White — Bright snappy
    {
        'name': 'alps',
        'click_freq_low': 3000, 'click_freq_high': 8500, 'click_amp': 0.60,
        'click_decay': 0.08, 'click_len_ms': 13,
        'body_freq': 500, 'body_drop_ratio': 0.60, 'body_amp': 0.28,
        'body_decay_ms': 45, 'body_len_ms': 65, 'body_wave': 'triangle',
        'thump_freq': 110, 'thump_amp': 0.30, 'thump_len_ms': 50, 'thump_decay_ms': 30,
        'tail_amp': 0.10, 'tail_lp': 2200, 'tail_len_ms': 50,
        'release_amp': 0.32, 'release_delay_ms': 55, 'release_freq_low': 2200, 'release_freq_high': 6500,
        'release_decay': 0.07,
        'total_ms': 170, 'randomize': 0.10,
    },
    # 8. Kailh Box White
    {
        'name': 'box-white',
        'click_freq_low': 4000, 'click_freq_high': 10000, 'click_amp': 0.70,
        'click_decay': 0.06, 'click_len_ms': 11,
        'body_freq': 520, 'body_drop_ratio': 0.55, 'body_amp': 0.30,
        'body_decay_ms': 50, 'body_len_ms': 70, 'body_wave': 'triangle',
        'thump_freq': 100, 'thump_amp': 0.32, 'thump_len_ms': 50, 'thump_decay_ms': 30,
        'tail_amp': 0.10, 'tail_lp': 2300, 'tail_len_ms': 50,
        'release_amp': 0.45, 'release_delay_ms': 50, 'release_freq_low': 2800, 'release_freq_high': 8000,
        'release_decay': 0.05,
        'total_ms': 175, 'randomize': 0.09,
    },
    # 9. Gateron Yellow — Smooth deep linear
    {
        'name': 'gateron-yellow',
        'click_freq_low': 1900, 'click_freq_high': 5000, 'click_amp': 0.40,
        'click_decay': 0.11, 'click_len_ms': 16,
        'body_freq': 340, 'body_drop_ratio': 0.65, 'body_amp': 0.32,
        'body_decay_ms': 60, 'body_len_ms': 75, 'body_wave': 'triangle',
        'thump_freq': 85, 'thump_amp': 0.45, 'thump_len_ms': 65, 'thump_decay_ms': 40,
        'tail_amp': 0.12, 'tail_lp': 1500, 'tail_len_ms': 50,
        'release_amp': 0.20, 'release_delay_ms': 70, 'release_freq_low': 1500, 'release_freq_high': 4500,
        'total_ms': 180, 'randomize': 0.10,
    },
    # 10. Holy Panda — Tactile clack
    {
        'name': 'holy-panda',
        'click_freq_low': 3200, 'click_freq_high': 7500, 'click_amp': 0.60,
        'click_decay': 0.08, 'click_len_ms': 14,
        'body_freq': 460, 'body_drop_ratio': 0.55, 'body_amp': 0.40,
        'body_decay_ms': 60, 'body_len_ms': 80, 'body_wave': 'triangle',
        'thump_freq': 105, 'thump_amp': 0.45, 'thump_len_ms': 60, 'thump_decay_ms': 38,
        'tail_amp': 0.13, 'tail_lp': 2000, 'tail_len_ms': 55,
        'release_amp': 0.30, 'release_delay_ms': 60, 'release_freq_low': 2200, 'release_freq_high': 6500,
        'release_decay': 0.07,
        'total_ms': 180, 'randomize': 0.10,
    },
    # 11. Silent MX — Dampened
    {
        'name': 'silent-mx',
        'click_freq_low': 1500, 'click_freq_high': 3500, 'click_amp': 0.20,
        'click_decay': 0.18, 'click_len_ms': 22,
        'body_freq': 310, 'body_drop_ratio': 0.60, 'body_amp': 0.18,
        'body_decay_ms': 60, 'body_len_ms': 70, 'body_wave': 'sine',
        'thump_freq': 75, 'thump_amp': 0.25, 'thump_len_ms': 60, 'thump_decay_ms': 45,
        'tail_amp': 0.06, 'tail_lp': 1000, 'tail_len_ms': 35,
        'release_amp': 0.05, 'release_delay_ms': 80, 'release_freq_low': 1000, 'release_freq_high': 3000,
        'total_ms': 160, 'randomize': 0.08,
    },
    # 12. Optical Linear — Clean fast
    {
        'name': 'optical',
        'click_freq_low': 2500, 'click_freq_high': 6500, 'click_amp': 0.50,
        'click_decay': 0.08, 'click_len_ms': 12,
        'body_freq': 400, 'body_drop_ratio': 0.65, 'body_amp': 0.22,
        'body_decay_ms': 40, 'body_len_ms': 50, 'body_wave': 'triangle',
        'thump_freq': 95, 'thump_amp': 0.30, 'thump_len_ms': 45, 'thump_decay_ms': 28,
        'tail_amp': 0.08, 'tail_lp': 1800, 'tail_len_ms': 35,
        'release_amp': 0.20, 'release_delay_ms': 55, 'release_freq_low': 1800, 'release_freq_high': 5000,
        'total_ms': 150, 'randomize': 0.09,
    },
    # 13. Typewriter — Vintage clackety
    {
        'name': 'typewriter',
        'click_freq_low': 4000, 'click_freq_high': 12000, 'click_amp': 0.85,
        'click_decay': 0.06, 'click_len_ms': 14,
        'body_freq': 700, 'body_drop_ratio': 0.45, 'body_amp': 0.45,
        'body_decay_ms': 80, 'body_len_ms': 100, 'body_wave': 'triangle',
        'thump_freq': 130, 'thump_amp': 0.50, 'thump_len_ms': 60, 'thump_decay_ms': 45,
        'tail_amp': 0.15, 'tail_lp': 3000, 'tail_len_ms': 70,
        'release_amp': 0.65, 'release_delay_ms': 45, 'release_freq_low': 3500, 'release_freq_high': 10500,
        'release_decay': 0.06,
        'total_ms': 200, 'randomize': 0.12,
    },
]


def main(out_root):
    out_root = Path(out_root)
    out_root.mkdir(parents=True, exist_ok=True)
    for pack_idx, preset in enumerate(PRESETS, 1):
        pack_dir = out_root / str(pack_idx)
        pack_dir.mkdir(exist_ok=True)
        for var_idx in range(1, 11):
            seed = pack_idx * 1000 + var_idx
            audio = synthesize_keystroke(preset, seed=seed)
            # 32-bit float WAV (원본과 같은 포맷)
            audio_f32 = audio.astype(np.float32)
            out_path = pack_dir / f'{pack_idx} ({var_idx}).wav'
            wavfile.write(str(out_path), SR, audio_f32)
        print(f"  Pack {pack_idx:2d} [{preset['name']:15s}] — 10 variations")
    print(f"\nDONE: 13 packs × 10 variations = 130 files")
    print(f"Output: {out_root}")


if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else 'public/soundFiles'
    main(target)
