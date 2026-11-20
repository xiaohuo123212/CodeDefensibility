import React from 'react';
import {AbsoluteFill} from 'remotion';
import {COLORS} from '../theme';

const GRID = '60px';

/**
 * C-V02：全片唯一背景层，静态多层 CSS 渐变。
 * CSS 的 background-image 列表是「先写在上层」，因此这里的顺序与
 * 契约要求的层序（base → 网格 → 光晕 → 暗角）相反。
 */
const backgroundImage = [
  'radial-gradient(ellipse at center, transparent 52%, rgba(0,0,0,0.5) 100%)',
  'radial-gradient(1200px 700px at 50% 44%, rgba(33,184,199,0.075), transparent 68%)',
  `linear-gradient(to right, rgba(255,255,255,0.025) 1px, transparent 1px)`,
  `linear-gradient(to bottom, rgba(255,255,255,0.025) 1px, transparent 1px)`,
  `linear-gradient(180deg, ${COLORS.bgTop} 0%, ${COLORS.bgMid} 55%, ${COLORS.bgBottom} 100%)`,
].join(', ');

export const Backdrop: React.FC = () => {
  return (
    <AbsoluteFill
      style={{
        backgroundImage,
        backgroundSize: `auto, auto, ${GRID} ${GRID}, ${GRID} ${GRID}, auto`,
        backgroundRepeat: 'no-repeat, no-repeat, repeat, repeat, no-repeat',
      }}
    >
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          height: 1,
          backgroundImage:
            'linear-gradient(90deg, transparent, rgba(33,184,199,0.35), transparent)',
        }}
      />
    </AbsoluteFill>
  );
};