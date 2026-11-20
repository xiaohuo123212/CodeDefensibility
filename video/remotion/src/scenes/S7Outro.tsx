import React from 'react';
import { AbsoluteFill, interpolate, useCurrentFrame } from 'remotion';
import { SceneStage } from '../components/SceneStage';
import daily from '../data/daily.json';
import { COLORS, FONT, LAYOUT, MOTION, RADIUS, SHADOW, SIZE, WEIGHT, easeOut } from '../theme';
import type { SceneProps } from '../types';

const CLAMP = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' } as const;

/** 文件行自右侧滑入的位移量（C-V09 S7：右滑落位 + scale 1.05→1，不回落）。 */
const DROP_X = 64;
const DROP_SCALE = 1.05;
/** 每行落地后左侧 accent 竖线闪一次的时长。 */
const FLASH_HOLD = 6;
const FLASH_FADE = 18;

const appear = (frame: number, start: number): React.CSSProperties => ({
  opacity: interpolate(frame, [start, start + MOTION.fade], [0, 1], { ...CLAMP, easing: easeOut }),
  transform: `translateY(${interpolate(frame, [start, start + MOTION.rise], [16, 0], {
    ...CLAMP,
    easing: easeOut,
  })}px)`,
});

export const S7Outro: React.FC<SceneProps> = ({ narration, range }) => {
  const frame = useCurrentFrame();
  const total = range.end - range.start;
  const files = daily.files;

  const rowStart = Math.round(total * 0.06);
  const rowStep = files.length > 0 ? Math.round((total * 0.34) / files.length) : 0;
  const outroStart = Math.round(total * 0.62);
  const activeIndex = rowStep > 0 ? Math.floor((frame - rowStart) / rowStep) : -1;

  const listDim = interpolate(frame, [outroStart, outroStart + MOTION.fade], [1, 0.4], {
    ...CLAMP,
    easing: easeOut,
  });

  return (
    <SceneStage scene="S7">
      <AbsoluteFill
        style={{
          padding: `${LAYOUT.padY}px ${LAYOUT.padX}px`,
          alignItems: 'center',
          justifyContent: 'center',
          fontFamily: FONT.sans,
        }}
      >
        <div style={{ width: LAYOUT.safeWidth, display: 'flex', flexDirection: 'column' }}>
          <div
            style={{
              padding: '40px 48px',
              borderRadius: RADIUS.card,
              border: `1px solid ${COLORS.line}`,
              backgroundColor: COLORS.raise,
              boxShadow: SHADOW.card,
              opacity: listDim,
              transform: `translateY(${interpolate(frame, [outroStart, outroStart + MOTION.fade], [0, -18], {
                ...CLAMP,
                easing: easeOut,
              })}px)`,
            }}
          >
            <div
              style={{
                fontFamily: FONT.mono,
                fontSize: SIZE.micro,
                letterSpacing: 1,
                color: COLORS.textDim,
                opacity: interpolate(frame, [4, 4 + MOTION.fade], [0, 1], { ...CLAMP, easing: easeOut }),
              }}
            >
              {daily.dirLabel}
            </div>

            <div style={{ marginTop: 22, display: 'flex', flexDirection: 'column', gap: 6 }}>
              {files.map((file, i) => {
                const isActive = i === activeIndex;
                const dropStart = rowStart + i * rowStep;
                const flashStart = dropStart + MOTION.rise;
                const flash = interpolate(
                  frame,
                  [flashStart, flashStart + FLASH_HOLD, flashStart + FLASH_FADE],
                  [0, 1, 0],
                  { ...CLAMP, easing: easeOut },
                );
                const barOpacity = Math.max(flash, isActive ? 1 : 0);
                return (
                  <div
                    key={file}
                    style={{
                      position: 'relative',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 18,
                      padding: '10px 20px',
                      borderRadius: RADIUS.sm,
                      borderLeft: '3px solid transparent',
                      backgroundColor: isActive ? COLORS.accentDim : 'transparent',
                      opacity: interpolate(
                        frame,
                        [dropStart, dropStart + MOTION.fade],
                        [0, 1],
                        { ...CLAMP, easing: easeOut },
                      ),
                      transform: `translateX(${interpolate(frame, [dropStart, dropStart + MOTION.fade], [DROP_X, 0], {
                        ...CLAMP,
                        easing: easeOut,
                      })}px) scale(${interpolate(frame, [dropStart, dropStart + MOTION.rise], [DROP_SCALE, 1], {
                        ...CLAMP,
                        easing: easeOut,
                      })})`,
                    }}
                  >
                    <span
                      style={{
                        position: 'absolute',
                        left: -3,
                        top: 0,
                        bottom: 0,
                        width: 3,
                        borderRadius: RADIUS.pill,
                        backgroundColor: COLORS.accent,
                        opacity: barOpacity,
                      }}
                    />
                    <span
                      style={{
                        fontFamily: FONT.mono,
                        fontSize: SIZE.small,
                        color: isActive ? COLORS.accent : COLORS.textDim,
                      }}
                    >
                      {String(i + 1).padStart(2, '0')}
                    </span>
                    <span
                      style={{
                        fontFamily: FONT.mono,
                        fontSize: SIZE.body,
                        color: isActive ? COLORS.text : COLORS.textBody,
                      }}
                    >
                      {`${daily.dirLabel}${file}`}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>

          <div
            style={{
              ...appear(frame, outroStart),
              marginTop: 48,
              fontSize: SIZE.body,
              fontWeight: WEIGHT.medium,
              lineHeight: 1.6,
              letterSpacing: 0.5,
              color: COLORS.text,
              textShadow: SHADOW.textSoft,
              maxWidth: LAYOUT.safeWidth,
            }}
          >
            {narration.s7Outro ?? ''}
          </div>
        </div>
      </AbsoluteFill>
    </SceneStage>
  );
};