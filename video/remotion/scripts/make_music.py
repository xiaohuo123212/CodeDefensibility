"""合成全片背景音乐：一段轻柔、缓慢、无打击的 C 大调 pad。

用户要求撤掉人声旁白、改用轻柔配乐，故本脚本生成 pubilc/audio/bgm.wav：
- 和弦每 12 秒一次、相邻段交叉淡入淡出，听感连续不断句
- 每个音叠两层轻微失谐（chorus 感），避免纯正弦的电子味
- 稀疏高音铃音做点缀，不做旋律，只做「空气感」
- 全局 3 秒淡入 / 5 秒淡出 + 24 秒周期的极轻呼吸

输出 32kHz 单声道 16bit，时长严格等于 totalFrames/fps（168.000s），
因此不需要音画对齐处理。
"""

import json
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
SR = 32000

# 频率表（C 大调，明亮、不悲伤）
A3, C4, D4, E4, F4, G4, A4, B4 = 220.00, 261.63, 293.66, 329.63, 349.23, 392.00, 440.00, 493.88
C5, D5, E5, G5 = 523.25, 587.33, 659.25, 783.99

# (低音根音, 和弦音)。每项 12 秒，循环使用。
CHORDS = [
    (C4, [C4, E4, G4, B4]),   # Cmaj7
    (A3, [A3, C4, E4, G4]),   # Am7
    (F4, [F4, A4, C5, E5]),   # Fmaj7
    (G4, [G4, B4, D5, G5]),   # G
    (E4, [E4, G4, B4, D5]),   # Em7
    (A3, [A3, C4, E4, G4]),   # Am7
    (F4, [F4, A4, C5, E5]),   # Fmaj7
    (G4, [G4, B4, D5, G5]),   # G
]
CHORD_DUR = 12.0
OVERLAP = 4.0  # 相邻和弦交叉的秒数，保证换和弦时不断层


def main() -> None:
    meta = json.loads((ROOT / "src/data/narration.json").read_text(encoding="utf-8"))
    duration = meta["totalFrames"] / meta["fps"]
    n = int(round(duration * SR))
    buf = np.zeros(n, dtype=np.float64)

    def add_pad(freq: float, t0: float, dur: float, amp: float) -> None:
        i0 = int(t0 * SR)
        i1 = min(n, int((t0 + dur) * SR))
        if i1 <= i0:
            return
        tt = np.arange(i1 - i0, dtype=np.float64) / SR
        w = 2 * np.pi * freq * tt
        # 基频 + 两次谐波，幅度递减，音色偏暖不刺耳
        sig = np.sin(w) + 0.32 * np.sin(2 * w) + 0.12 * np.sin(3 * w)
        # 失谐层制造极缓的拍频，听感更像真实合奏
        w2 = 2 * np.pi * freq * 1.0025 * tt
        sig = sig + 0.55 * (np.sin(w2) + 0.30 * np.sin(2 * w2))
        env = np.ones(i1 - i0, dtype=np.float64)
        a = min(int(3.5 * SR), len(env))
        r = min(int(OVERLAP * SR), len(env))
        env[:a] = np.sin(np.linspace(0, np.pi / 2, a)) ** 2
        env[-r:] *= np.sin(np.linspace(np.pi / 2, 0, r)) ** 2
        buf[i0:i1] += amp * sig * env

    n_seg = int(np.ceil(duration / CHORD_DUR))
    for k in range(n_seg):
        t0 = k * CHORD_DUR
        root, notes = CHORDS[k % len(CHORDS)]
        add_pad(root / 2, t0, CHORD_DUR + OVERLAP, 0.10)  # 低音暖垫
        for f in notes:
            add_pad(f, t0, CHORD_DUR + OVERLAP, 0.16)

    def add_bell(freq: float, t0: float) -> None:
        i0 = int(t0 * SR)
        if i0 >= n:
            return
        tt = np.arange(n - i0, dtype=np.float64) / SR
        w = 2 * np.pi * freq * tt
        sig = np.sin(w) + 0.25 * np.sin(2.01 * w)
        env = np.exp(-tt / 1.4)
        buf[i0:] += 0.05 * sig * env

    # 每 16 秒一次高音点缀，落在当前和弦的最高音上，不构成旋律
    t = 4.0
    while t < duration - 6.0:
        _, notes = CHORDS[int(t // CHORD_DUR) % len(CHORDS)]
        add_bell(notes[-1] * 2, t)
        t += 16.0

    # 全局淡入淡出 + 极轻呼吸（周期 24 秒，深度 12%）
    tt = np.arange(n, dtype=np.float64) / SR
    env = np.ones(n, dtype=np.float64)
    fi, fo = int(3 * SR), int(5 * SR)
    env[:fi] = np.linspace(0, 1, fi) ** 1.5
    env[-fo:] = np.linspace(1, 0, fo) ** 1.5
    buf *= env * (1 + 0.12 * np.sin(2 * np.pi * tt / 24.0))

    peak = float(np.max(np.abs(buf)))
    buf = buf / peak * 0.30  # 峰值约 -10.5 dBFS，再由播放端压一档

    pcm = np.clip(buf * 32767.0, -32768, 32767).astype("<i2")
    out = ROOT / "public/audio/bgm.wav"
    out.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(pcm.tobytes())

    print(f"{out}  {duration:.3f}s  {SR}Hz mono  {out.stat().st_size / 1048576:.1f}MB")
    assert abs(len(pcm) / SR - duration) < 0.01, "音频时长必须与视频严格一致"


if __name__ == "__main__":
    main()