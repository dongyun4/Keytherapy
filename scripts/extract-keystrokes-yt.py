"""
유튜브 영상 wav 에서 깨끗한 키스트로크 10개 자동 추출 → 사이트 사운드 팩으로 통합.

처리 흐름 (영상 1개당):
  1. 첫 5분 모노 22050Hz 로 stream 로드 (전체 파일 메모리 폭발 방지)
  2. librosa onset_detect 로 키스트로크 시점 검출 (BGM·노이즈 무시 위해 highpass 1kHz)
  3. 각 onset 에서 130ms 짜리 윈도우 추출
  4. RMS 에너지 기준 상위 80% 안에서 균등 간격으로 10개 sampling
     (너무 큰 transient 만 모이지 않게 + 시간상 분산)
  5. 각 클립 — fade in/out 5ms + 피크 -3dBFS 노멀라이즈
  6. public/soundFiles/<slot>/ 에 1~10.wav 저장
  7. import-all-packs.py 의 KEYBOARD_PACKS 끝에 12개 새 팩 등록 (slot 27~38)
"""

import os
import sys
import json
import shutil
from pathlib import Path

import numpy as np
import librosa
import soundfile as sf
from scipy.signal import butter, sosfiltfilt

# ── 설정 ────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'yt-audio'
DEST = ROOT / 'public' / 'soundFiles'
SLOT_START = 27   # 기존 26개 키보드 팩 다음 슬롯부터

SAMPLE_RATE = 22050
ANALYZE_DUR = 300              # 첫 5분만 분석
CLIP_DUR_MS = 130              # 키스트로크 클립 길이 (130ms)
PRE_ONSET_MS = 12              # onset 앞 버퍼
FADE_MS = 5                    # 시작·끝 fade
HIGHPASS_HZ = 1000             # 1kHz 미만 BGM·rumble 제거 (감지용)
MIN_GAP_MS = 60                # 최소 keystroke 간격 (이중 감지 방지)
TARGET_KEYSTROKES = 10
PEAK_dBFS = -3                 # 노멀라이즈 목표 피크

# 라벨 + 영상 메타데이터 (사이트 표시용)
PACKS = [
    ('🎬 키테라피 ① 추출', 'gThrJH6XzV4', 'yt-01.wav'),
    ('🎬 키테라피 ② 추출', 'mgrYqO3D0V4', 'yt-02.wav'),
    ('🎬 키테라피 ③ 추출', 'MVWyZyV5FOo', 'yt-03.wav'),
    ('🎬 키테라피 ④ 추출', 'tl0HqKErDfM', 'yt-04.wav'),
    ('🎬 키테라피 ⑤ 추출', 'iBXfUgfgx3g', 'yt-05.wav'),
    ('🎬 키테라피 ⑥ 추출', '7p0I0o972fc', 'yt-06.wav'),
    ('🎬 키테라피 ⑦ 추출', 'f7aE8r_KgCM', 'yt-07.wav'),
    ('🎬 키테라피 ⑧ 추출', 'oK6R3y0--Ic', 'yt-08.wav'),
    ('🎬 키테라피 ⑨ 추출', 'A_64HcPvu58', 'yt-09.wav'),
    ('🎬 키테라피 ⑩ 추출', 'VsX7o5IbBvU', 'yt-10.wav'),
    ('🎬 키테라피 ⑪ 추출', 'oqt1Mky-dfQ', 'yt-11.wav'),
    ('🎬 키테라피 ⑫ 추출', 'fBX0mNUb7ro', 'yt-12.wav'),
]


def highpass(audio: np.ndarray, sr: int, cutoff: float = HIGHPASS_HZ) -> np.ndarray:
    """1kHz 하이패스 — BGM·rumble 제거해 onset 감지 정확도↑"""
    sos = butter(4, cutoff / (sr / 2), btype='highpass', output='sos')
    return sosfiltfilt(sos, audio).astype(np.float32)


def detect_onsets(audio: np.ndarray, sr: int) -> np.ndarray:
    """키스트로크 시점 (samples). highpass → onset_detect."""
    hp = highpass(audio, sr)
    onsets = librosa.onset.onset_detect(
        y=hp, sr=sr,
        units='samples',
        backtrack=True,
        delta=0.07,
        wait=int(MIN_GAP_MS * sr / 1000 / 512),
        pre_avg=4, post_avg=4,
        pre_max=4, post_max=4,
    )
    return onsets


def score_keystroke(audio: np.ndarray, sr: int, start: int, dur_samples: int) -> float:
    """클립의 '깨끗함' 점수: RMS 높고, transient 비율 높을수록 좋음."""
    end = min(start + dur_samples, len(audio))
    if end - start < dur_samples * 0.5:
        return 0.0
    clip = audio[start:end]
    rms = float(np.sqrt(np.mean(clip ** 2)))
    if rms < 1e-5:
        return 0.0
    # 첫 30ms 가 후반보다 클수록 keystroke 다움 (decay 형태)
    head_n = int(sr * 0.030)
    tail_n = max(1, len(clip) - head_n)
    head = float(np.sqrt(np.mean(clip[:head_n] ** 2))) if head_n > 0 else 0.0
    tail = float(np.sqrt(np.mean(clip[head_n:] ** 2))) if tail_n > 0 else 1.0
    transient_ratio = head / (tail + 1e-9)
    return rms * (1.0 + min(transient_ratio, 5.0))


def extract_clips(audio: np.ndarray, sr: int) -> list[np.ndarray]:
    """깨끗한 키스트로크 10개 추출."""
    onsets = detect_onsets(audio, sr)
    if len(onsets) < TARGET_KEYSTROKES:
        print(f"   ⚠️  onset {len(onsets)}개만 감지됨 (목표 {TARGET_KEYSTROKES}+)")

    pre = int(sr * PRE_ONSET_MS / 1000)
    dur = int(sr * CLIP_DUR_MS / 1000)
    fade = int(sr * FADE_MS / 1000)

    # 점수 + onset → 정렬용
    scored = []
    for o in onsets:
        start = max(0, o - pre)
        s = score_keystroke(audio, sr, start, dur)
        scored.append((s, start))
    # 점수 상위 30% 만 후보
    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[: max(TARGET_KEYSTROKES * 4, 40)]
    # 후보 중 시간상 균등 분산 — 가까운 것 제거
    top.sort(key=lambda x: x[1])  # 시간순
    selected = []
    last_end = -10**9
    for sc, st in top:
        if st - last_end < int(sr * 0.250):  # 250ms 간격
            continue
        selected.append((sc, st))
        last_end = st + dur
    # 점수 다시 상위 N
    selected.sort(key=lambda x: x[0], reverse=True)
    selected = selected[:TARGET_KEYSTROKES]
    selected.sort(key=lambda x: x[1])  # 시간순 재정렬

    # 클립 잘라서 후처리
    clips = []
    for _, st in selected:
        end = st + dur
        clip = audio[st:end].copy()
        if len(clip) < dur:
            clip = np.pad(clip, (0, dur - len(clip)))
        # fade in/out
        if fade > 0:
            ramp = np.linspace(0, 1, fade)
            clip[:fade] *= ramp
            clip[-fade:] *= ramp[::-1]
        # peak 노멀라이즈 → -3dBFS
        peak = float(np.max(np.abs(clip)))
        if peak > 1e-6:
            target = 10 ** (PEAK_dBFS / 20)
            clip = clip * (target / peak)
        clips.append(clip.astype(np.float32))
    return clips


def process_video(label: str, video_id: str, wav_name: str, slot: int) -> bool:
    src_path = SRC / wav_name
    if not src_path.exists():
        print(f"  ❌ {wav_name} 없음 — 스킵")
        return False
    print(f"  📥 {wav_name} 분석 중 (첫 {ANALYZE_DUR}s)...")
    try:
        # offset=0, duration=N — librosa 가 디스크에서 부분만 읽어 메모리 절약
        audio, sr = librosa.load(str(src_path),
                                  sr=SAMPLE_RATE, mono=True,
                                  offset=0, duration=ANALYZE_DUR)
    except Exception as e:
        print(f"  ❌ load 실패: {e}")
        return False
    print(f"     로드 완료 ({len(audio)/sr:.1f}s)")

    clips = extract_clips(audio, sr)
    if not clips:
        print(f"  ❌ keystroke 추출 0개 — 스킵")
        return False

    # 출력 저장
    out_dir = DEST / str(slot)
    out_dir.mkdir(parents=True, exist_ok=True)
    # 기존 파일 정리
    for f in out_dir.iterdir():
        if f.is_file():
            try: f.unlink()
            except: pass
    for i, clip in enumerate(clips, 1):
        out_path = out_dir / f"{slot} ({i}).wav"
        sf.write(str(out_path), clip, sr, subtype='PCM_16')
    print(f"  ✓ Slot {slot} → {len(clips)} 클립 저장 ({label})")
    return True


def main():
    if not SRC.exists():
        print(f"❌ {SRC} 없음 — yt-audio/ 다운로드 먼저")
        return
    print(f"키스트로크 추출 시작 — 총 {len(PACKS)} 영상")
    print("=" * 60)
    success_packs = []  # (slot, label, video_id) 성공한 것
    for i, (label, vid, wav) in enumerate(PACKS):
        slot = SLOT_START + i
        print(f"\n[Slot {slot}] {label}")
        if process_video(label, vid, wav, slot):
            success_packs.append((slot, label, vid))
    print("\n" + "=" * 60)
    print(f"완료: {len(success_packs)} / {len(PACKS)} 팩")
    # 결과 메타 — import-all-packs.py 업데이트용 JSON 출력
    meta_path = ROOT / 'scripts' / 'yt-extracted-packs.json'
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump([{'slot': s, 'label': l, 'video_id': v} for s, l, v in success_packs],
                  f, ensure_ascii=False, indent=2)
    print(f"메타: {meta_path}")


if __name__ == '__main__':
    main()
