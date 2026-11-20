import React from 'react';
import { AbsoluteFill, interpolate, useCurrentFrame } from 'remotion';
import type { SceneProps } from '../types';
import { SceneStage } from '../components/SceneStage';
import {
  COLORS,
  FONT,
  LAYOUT,
  MOTION,
  RADIUS,
  SHADOW,
  SIZE,
  WEIGHT,
  easeInOut,
  easeOut,
} from '../theme';
import spec from '../data/report-fx-spec.json';

const CLAMP = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' } as const;

const PANEL_WIDTH = 1560;
/** 第二句点名「高性能」的时刻（相对本镜头的帧），强调行在此入场并做一次扫描 */
const EMPHASIS_AT = 120;
/** C-V09：需求行按 8 帧 stagger 依次出现 */
const LINE_STAGGER = 8;
/** C-V09：5 / 4 / 1 三个数字各做 10 帧整数计数 */
const COUNT_FRAMES = 10;
const COUNT_STAGGER = 8;
/** C-V09：「高性能」行一次 12 帧扫描高亮 */
const SCAN_FRAMES = 12;
const SCAN_FADE = 3;

const { precheck } = spec;
const focusItem = precheck.items[0];

const revealAt = (frame: number, start: number, risePx = 18): React.CSSProperties => ({
  opacity: interpolate(frame, [start, start + MOTION.fade], [0, 1], { ...CLAMP, easing: easeOut }),
  transform: `translateY(${interpolate(frame, [start, start + MOTION.rise], [risePx, 0], {
    ...CLAMP,
    easing: easeOut,
  })}px)`,
});

const lineReveal = (index: number): number => 12 + index * LINE_STAGGER;

/** 纯整数计数，从 0 跳到目标值，不出现小数。 */
const countUp = (frame: number, start: number, target: number): number =>
  Math.round(
    interpolate(frame, [start, start + COUNT_FRAMES], [0, target], { ...CLAMP, easing: easeOut }),
  );

const SUMMARY_TOKENS = precheck.summary.split(/(\d+)/).filter((token) => token.length > 0);

export const S3Precheck: React.FC<SceneProps> = () => {
  const frame = useCurrentFrame();

  const summaryStart = lineReveal(2);
  let digitOrder = 0;
  const summaryNodes = SUMMARY_TOKENS.map((token, index) => {
    if (!/^\d+$/.test(token)) {
      return <React.Fragment key={index}>{token}</React.Fragment>;
    }
    const start = summaryStart + 4 + digitOrder * COUNT_STAGGER;
    digitOrder += 1;
    return (
      <span key={index} style={{ color: COLORS.accent, fontWeight: WEIGHT.semibold }}>
        {countUp(frame, start, Number(token))}
      </span>
    );
  });

  const scanOpacity = interpolate(
    frame,
    [
      EMPHASIS_AT,
      EMPHASIS_AT + SCAN_FADE,
      EMPHASIS_AT + SCAN_FRAMES - SCAN_FADE,
      EMPHASIS_AT + SCAN_FRAMES,
    ],
    [0, 1, 1, 0],
    CLAMP,
  );
  const scanOffset = interpolate(
    frame,
    [EMPHASIS_AT, EMPHASIS_AT + SCAN_FRAMES],
    [-100, 180],
    { ...CLAMP, easing: easeInOut },
  );

  return (
    <SceneStage scene="S3">
      <AbsoluteFill
        style={{
          alignItems: 'center',
          justifyContent: 'center',
          paddingTop: LAYOUT.padY,
          paddingBottom: 170,
          paddingLeft: LAYOUT.padX,
          paddingRight: LAYOUT.padX,
          fontFamily: FONT.sans,
        }}
      >
        <div
          style={{
            width: PANEL_WIDTH,
            padding: '48px 52px 52px',
            backgroundColor: COLORS.raise,
            border: `1px solid ${COLORS.line}`,
            borderRadius: RADIUS.card,
            boxShadow: SHADOW.card,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <span
              style={{
                width: 4,
                height: 26,
                borderRadius: 2,
                backgroundColor: COLORS.accent,
              }}
            />
            <span
              style={{
                flex: 1,
                fontSize: SIZE.body,
                fontWeight: WEIGHT.semibold,
                color: COLORS.text,
              }}
            >
              {spec.title}
            </span>
            <span
              style={{
                fontFamily: FONT.mono,
                fontSize: SIZE.micro,
                color: COLORS.textDim,
              }}
            >
              {spec.sourceMd}
            </span>
          </div>

          <div
            style={{
              marginTop: 30,
              height: 1,
              backgroundColor: COLORS.lineSoft,
            }}
          />

          <div
            style={{
              marginTop: 28,
              fontSize: SIZE.small,
              color: COLORS.textMuted,
              lineHeight: 1.6,
              ...revealAt(frame, lineReveal(0)),
            }}
          >
            {spec.lead}
          </div>

          <div
            style={{
              marginTop: 34,
              fontSize: SIZE.body,
              fontWeight: WEIGHT.semibold,
              color: COLORS.textBody,
              ...revealAt(frame, lineReveal(1)),
            }}
          >
            {precheck.heading}
          </div>

          <div
            style={{
              marginTop: 14,
              fontSize: SIZE.small,
              color: COLORS.textMuted,
              ...revealAt(frame, summaryStart),
            }}
          >
            {summaryNodes}
          </div>

          {focusItem ? (
            <div
              style={{
                position: 'relative',
                overflow: 'hidden',
                marginTop: 30,
                padding: '22px 28px',
                background: COLORS.accentDim,
                borderLeft: `3px solid ${COLORS.accent}`,
                borderRadius: RADIUS.panel,
                boxShadow: scanOpacity > 0.001 ? `0 0 40px ${COLORS.accentGlow}` : undefined,
                ...revealAt(frame, lineReveal(3)),
              }}
            >
              <div
                style={{
                  position: 'absolute',
                  inset: 0,
                  overflow: 'hidden',
                  borderRadius: RADIUS.panel,
                  pointerEvents: 'none',
                }}
              >
                <div
                  style={{
                    position: 'absolute',
                    left: 0,
                    right: 0,
                    height: '70%',
                    background: `linear-gradient(180deg, transparent 0%, ${COLORS.accentDim} 45%, ${COLORS.accentGlow} 55%, transparent 100%)`,
                    opacity: scanOpacity,
                    transform: `translateY(${scanOffset}%)`,
                  }}
                />
              </div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 20 }}>
                <span
                  style={{
                    fontFamily: FONT.mono,
                    fontSize: SIZE.micro,
                    color: COLORS.textMuted,
                  }}
                >
                  {focusItem.location}
                </span>
                <span style={{ fontSize: SIZE.small, color: COLORS.textBody }}>
                  「
                  <span style={{ color: COLORS.accent, fontWeight: WEIGHT.semibold }}>
                    {focusItem.term}
                  </span>
                  」
                </span>
              </div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 14, marginTop: 14 }}>
                <span style={{ fontSize: SIZE.small, color: COLORS.textDim }}>→</span>
                <span style={{ fontSize: SIZE.small, color: COLORS.textBody }}>
                  {focusItem.criteria}
                </span>
              </div>
            </div>
          ) : null}
        </div>
      </AbsoluteFill>
    </SceneStage>
  );
};