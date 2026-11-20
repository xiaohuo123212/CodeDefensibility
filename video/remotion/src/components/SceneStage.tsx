import React from 'react';
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from 'remotion';
import { easeOut } from '../theme';
import type { SceneId } from '../types';

/**
 * 全片统一的镜头舞台（C-V07）。
 *
 * 外层只负责铺满画面且保持透明，让 Backdrop 透出；相机变换与进出场
 * 都落在内层，避免 scene 根节点的 opacity 与这里的转场互相覆盖。
 */

// 相机呼吸上限：超过 1.03 会让边缘文字发虚，且位移需同步收小
const CAM_MAX = 1.028;
const PAN_X = 12;
const PAN_Y = 10;
const ENTER_FRAMES = 10;
const ENTER_SCALE = 1.035;
const EXIT_FRAMES = 8;
const EXIT_SCALE = 1.015;

const CLAMP = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' } as const;

/** S1=0 … S7=6，用于决定推近/拉远与位移方向。 */
const sceneIndex = (scene: SceneId): number => Number(scene.slice(1)) - 1;

export const SceneStage: React.FC<{ scene: SceneId; children: React.ReactNode }> = ({ scene, children }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const index = sceneIndex(scene);

  // 匀速推进才像运镜，缓出会像元素动画，因此相机层面不给 easing
  const progress = interpolate(frame, [0, Math.max(durationInFrames - 1, 1)], [0, 1], CLAMP);
  const camScale =
    index % 2 === 0
      ? interpolate(progress, [0, 1], [1, CAM_MAX])
      : interpolate(progress, [0, 1], [CAM_MAX, 1]);

  const panAlongX = index % 4 < 2;
  const panOffset = panAlongX
    ? interpolate(progress, [0, 1], [-PAN_X, PAN_X])
    : interpolate(progress, [0, 1], [-PAN_Y, PAN_Y]);

  const enterScale = interpolate(frame, [0, ENTER_FRAMES], [ENTER_SCALE, 1], { ...CLAMP, easing: easeOut });
  const enterOpacity = interpolate(frame, [0, ENTER_FRAMES], [0, 1], { ...CLAMP, easing: easeOut });

  const exitStart = Math.max(durationInFrames - EXIT_FRAMES, 0);
  const exitScale = interpolate(frame, [exitStart, durationInFrames], [1, EXIT_SCALE], CLAMP);
  const exitOpacity = interpolate(frame, [exitStart, durationInFrames], [1, 0], CLAMP);

  return (
    <AbsoluteFill style={{ backgroundColor: 'transparent' }}>
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          opacity: enterOpacity * exitOpacity,
          transform: `translate(${panAlongX ? panOffset : 0}px, ${panAlongX ? 0 : panOffset}px) scale(${
            camScale * enterScale * exitScale
          })`,
          transformOrigin: 'center center',
        }}
      >
        {children}
      </div>
    </AbsoluteFill>
  );
};