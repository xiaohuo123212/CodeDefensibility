import React from 'react';
import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame } from 'remotion';
import { SceneStage } from '../components/SceneStage';
import { COLORS, FONT, LAYOUT, MOTION, RADIUS, SHADOW, easeInOut, easeOut } from '../theme';
import type { SceneProps } from '../types';

const CLAMP = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' } as const;

// 白底 PPT 页放进深色画框：16:9 内容区 + 四周留白 90/160px（≥64px）。
const FRAME_WIDTH = LAYOUT.safeWidth;
const FRAME_HEIGHT = 900;
// 两页并排成一个 200% 宽的 track，翻页靠整体横移 50%，中途两页各自只在半幅内可见，
// 彻底避免「交叉淡化时整页文字重叠成重影」。
const SLIDE_FRAMES = 16;
// P13 为实测数字页，画框内缘以「青色微光」呼吸缓和白底页接进深色框的硬切；
// 不做整页 opacity 呼吸，避免白底页在深色框里肉眼可见地闪。
const BREATH_PERIOD = 40;
const BREATH_MIN = 0.72;

const PAGE: React.CSSProperties = {
  width: '100%',
  height: '100%',
  objectFit: 'contain',
  display: 'block',
};

export const S6Metrics: React.FC<SceneProps> = ({ range }) => {
  const frame = useCurrentFrame();
  const total = range.end - range.start;
  const cut = Math.round(total * 0.5);

  // 0 = 停在第 1 页，1 = 停在第 2 页；中间整段平移。
  const slide = interpolate(frame, [cut, cut + SLIDE_FRAMES], [0, 1], {
    ...CLAMP,
    easing: easeInOut,
  });

  const breath = interpolate(
    frame % BREATH_PERIOD,
    [0, BREATH_PERIOD / 2, BREATH_PERIOD],
    [1, BREATH_MIN, 1],
    { ...CLAMP, easing: easeInOut },
  );

  const frameIn = interpolate(frame, [0, MOTION.rise], [0, 1], { ...CLAMP, easing: easeOut });
  const frameScale = interpolate(frame, [0, MOTION.rise], [0.988, 1], {
    ...CLAMP,
    easing: easeOut,
  });

  return (
    <SceneStage scene="S6">
      <AbsoluteFill
        style={{ alignItems: 'center', justifyContent: 'center', fontFamily: FONT.sans }}
      >
        <div
          style={{
            position: 'relative',
            width: FRAME_WIDTH,
            height: FRAME_HEIGHT,
            borderRadius: RADIUS.card,
            border: `1px solid ${COLORS.line}`,
            backgroundColor: COLORS.termBg,
            boxShadow: SHADOW.card,
            overflow: 'hidden',
            opacity: frameIn,
            transform: `scale(${frameScale})`,
          }}
        >
          <div
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '200%',
              height: '100%',
              display: 'flex',
              transform: `translateX(${-50 * slide}%)`,
            }}
          >
            <div style={{ position: 'relative', width: '50%', height: '100%' }}>
              <Img src={staticFile('ppt/P13.png')} style={PAGE} />
            </div>
            <div style={{ position: 'relative', width: '50%', height: '100%' }}>
              <Img src={staticFile('ppt/P15.png')} style={PAGE} />
            </div>
          </div>
          {/* 翻页缓和：呼吸落在画框内缘的青色微光上（inset 不会被 overflow 裁掉） */}
          <div
            style={{
              position: 'absolute',
              inset: 0,
              borderRadius: RADIUS.card,
              border: `1px solid ${COLORS.accent}`,
              boxShadow: `inset 0 0 30px ${COLORS.accentGlow}`,
              opacity: (1 - breath) * 3,
              pointerEvents: 'none',
            }}
          />
        </div>
      </AbsoluteFill>
    </SceneStage>
  );
};