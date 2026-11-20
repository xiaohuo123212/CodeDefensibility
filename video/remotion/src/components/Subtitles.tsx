import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {COLORS, LAYOUT, SHADOW, SIZE, WEIGHT, easeOut} from '../theme';
import type {Narration, SceneId} from '../types';

/** S1 标题两行与 S7 收尾一行由各自 scene 渲染，避免重复显示。 */
const SCENES_WITHOUT_SUBTITLES: SceneId[] = ['S1', 'S7'];

const FADE_FRAMES = 8;
const RISE_PX = 10;
const SCRIM_HEIGHT = 260;

export const Subtitles: React.FC<{narration: Narration}> = ({narration}) => {
  const frame = useCurrentFrame();
  const sentence = narration.sentences.find(
    (item) =>
      !SCENES_WITHOUT_SUBTITLES.includes(item.scene) &&
      item.startFrame <= frame &&
      frame <= item.endFrame,
  );

  const localFrame = sentence ? frame - sentence.startFrame : 0;
  const progress = interpolate(localFrame, [0, FADE_FRAMES], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: easeOut,
  });

  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      {sentence ? (
        <div
          style={{
            position: 'absolute',
            left: 0,
            right: 0,
            bottom: 0,
            height: SCRIM_HEIGHT,
            backgroundImage: 'linear-gradient(to top, rgba(0,0,0,0.82), transparent)',
          }}
        />
      ) : null}
      <AbsoluteFill
        style={{
          justifyContent: 'flex-end',
          alignItems: 'center',
          paddingBottom: LAYOUT.subtitleBottom,
        }}
      >
        {sentence ? (
          <div
            style={{
              maxWidth: LAYOUT.safeWidth,
              paddingLeft: 32,
              paddingRight: 32,
              fontSize: SIZE.body,
              fontWeight: WEIGHT.medium,
              color: COLORS.text,
              textShadow: SHADOW.text,
              letterSpacing: 0.5,
              lineHeight: 1.5,
              textAlign: 'center',
              whiteSpace: 'pre-wrap',
              opacity: progress,
              transform: `translateY(${(1 - progress) * RISE_PX}px)`,
            }}
          >
            {sentence.text}
          </div>
        ) : null}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};