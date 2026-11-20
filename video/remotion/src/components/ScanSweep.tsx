import React from 'react';
import { interpolate, useCurrentFrame } from 'remotion';
import { COLORS, easeInOut } from '../theme';

const CLAMP = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' } as const;

/** 两端淡入淡出帧数（C-V08 固定 6 帧）。 */
const EDGE_FRAMES = 6;
/** 光带中心的亮线粗细，给扫描一个明确的「锋面」。 */
const CORE = 3;

const withAlpha = (color: string, alpha: number): string => {
  const match = /^#([0-9a-f]{6})$/i.exec(color);
  if (!match) return color;
  const value = parseInt(match[1], 16);
  return `rgba(${(value >> 16) & 255}, ${(value >> 8) & 255}, ${value & 255}, ${alpha})`;
};

/**
 * 扫描光带（C-V08）：沿父容器纵向自上而下扫过一次。
 * 父容器必须 position: relative + overflow: hidden。
 */
export const ScanSweep: React.FC<{
  from: number;
  to: number;
  height: number;
  color?: string;
}> = ({ from, to, height, color = COLORS.accent }) => {
  const frame = useCurrentFrame();
  if (frame < from || frame > to) return null;

  const edge = Math.max(1, Math.min(EDGE_FRAMES, (to - from) / 2));
  const progress = interpolate(frame, [from, to], [0, 1], { ...CLAMP, easing: easeInOut });
  const opacity = interpolate(frame, [from, from + edge, to - edge, to], [0, 1, 1, 0], CLAMP);

  return (
    <div
      style={{
        position: 'absolute',
        left: 0,
        right: 0,
        top: `${progress * 100}%`,
        height,
        transform: 'translateY(-50%)',
        opacity,
        pointerEvents: 'none',
        background: `linear-gradient(180deg, ${withAlpha(color, 0)}, ${withAlpha(color, 0.12)} 30%, ${withAlpha(
          color,
          0.45,
        )} 50%, ${withAlpha(color, 0.12)} 70%, ${withAlpha(color, 0)})`,
      }}
    >
      <div
        style={{
          position: 'absolute',
          top: (height - CORE) / 2,
          left: 0,
          right: 0,
          height: CORE,
          background: withAlpha(color, 0.85),
          boxShadow: `0 0 18px ${withAlpha(color, 0.55)}`,
        }}
      />
    </div>
  );
};