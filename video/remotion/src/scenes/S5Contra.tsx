import React from 'react';
import { AbsoluteFill, interpolate, useCurrentFrame } from 'remotion';
import { SceneStage } from '../components/SceneStage';
import report from '../data/report-fx-contradicted.json';
import { COLORS, FONT, LAYOUT, MOTION, RADIUS, SHADOW, SIZE, WEIGHT, easeOut } from '../theme';
import type { SceneProps } from '../types';

const CLAMP = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' } as const;

/** 定位行号的入场对焦：14 帧内由失焦到锐利（C-V09 S5）。 */
const FOCUS_START = 10;
const FOCUS_FRAMES = 14;
const FOCUS_BLUR = 8;

/** 证据条目逐个点亮 accent 圆点的节奏（每项间隔 10 帧）。 */
const EVIDENCE_FOCUS_START = 96;
const EVIDENCE_FOCUS_STEP = 10;
const EVIDENCE_FOCUS_FRAMES = 8;

const appear = (frame: number, start: number): React.CSSProperties => ({
  opacity: interpolate(frame, [start, start + MOTION.fade], [0, 1], { ...CLAMP, easing: easeOut }),
  transform: `translateY(${interpolate(frame, [start, start + MOTION.rise], [16, 0], {
    ...CLAMP,
    easing: easeOut,
  })}px)`,
});

const splitLocation = (line: string): { label: string; ref: string } => {
  const sep = line.lastIndexOf('：');
  return sep >= 0
    ? { label: line.slice(0, sep), ref: line.slice(sep + 1) }
    : { label: '', ref: line };
};

const toPairs = (lines: string[]): { label: string; ref: string }[] => {
  const pairs: { label: string; ref: string }[] = [];
  for (let i = 0; i < lines.length; i += 2) {
    pairs.push({ label: lines[i], ref: lines[i + 1] ?? '' });
  }
  return pairs;
};

export const S5Contra: React.FC<SceneProps> = () => {
  const frame = useCurrentFrame();
  const location = splitLocation(report.locationLine);
  const pairs = toPairs(report.evidenceLines);

  const focusBlur = interpolate(frame, [FOCUS_START, FOCUS_START + FOCUS_FRAMES], [FOCUS_BLUR, 0], {
    ...CLAMP,
    easing: easeOut,
  });

  return (
    <SceneStage scene="S5">
      <AbsoluteFill
        style={{
          padding: `${LAYOUT.padY}px ${LAYOUT.padX}px`,
          justifyContent: 'center',
          alignItems: 'center',
          fontFamily: FONT.sans,
          color: COLORS.text,
        }}
      >
        <div style={{ width: LAYOUT.safeWidth, display: 'flex', flexDirection: 'column' }}>
          <div
            style={{
              ...appear(frame, 4),
              display: 'flex',
              alignItems: 'center',
              gap: 14,
              fontSize: SIZE.micro,
              fontWeight: WEIGHT.medium,
              letterSpacing: 1,
              color: COLORS.textDim,
            }}
          >
            <span style={{ width: 4, height: SIZE.micro, borderRadius: RADIUS.pill, backgroundColor: COLORS.accent }} />
            {report.title}
          </div>

          <div
            style={{
              ...appear(frame, FOCUS_START),
              marginTop: 36,
              display: 'flex',
              alignItems: 'baseline',
              gap: 20,
              padding: '26px 40px',
              borderRadius: RADIUS.card,
              border: `1px solid ${COLORS.line}`,
              backgroundColor: COLORS.raise,
              boxShadow: SHADOW.card,
            }}
          >
            {location.label ? (
              <span style={{ fontSize: SIZE.small, fontWeight: WEIGHT.medium, color: COLORS.textMuted }}>
                {location.label}
              </span>
            ) : null}
            <span
              style={{
                fontFamily: FONT.mono,
                fontSize: SIZE.headline,
                fontWeight: WEIGHT.semibold,
                color: COLORS.accent,
                filter: `blur(${focusBlur}px)`,
              }}
            >
              {location.ref}
            </span>
          </div>

          <div
            style={{
              ...appear(frame, 34),
              marginTop: 44,
              fontSize: SIZE.headline,
              fontWeight: WEIGHT.bold,
              lineHeight: 1.3,
              color: COLORS.text,
            }}
          >
            {report.conclusionLine}
          </div>

          <div
            style={{
              ...appear(frame, 62),
              marginTop: 32,
              padding: '30px 40px',
              borderRadius: RADIUS.card,
              borderLeft: `3px solid ${COLORS.accent}`,
              backgroundColor: COLORS.raiseSoft,
              fontSize: SIZE.body,
              fontWeight: WEIGHT.regular,
              lineHeight: 1.55,
              color: COLORS.textBody,
            }}
          >
            {report.requirementLine}
          </div>

          <div
            style={{
              ...appear(frame, 96),
              marginTop: 36,
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: '12px 48px',
            }}
          >
            {pairs.map((pair, i) => {
              const conflict = Boolean(pair.ref) && pair.ref === location.ref;
              const focusStart = EVIDENCE_FOCUS_START + i * EVIDENCE_FOCUS_STEP;
              const dotOpacity = interpolate(
                frame,
                [focusStart, focusStart + EVIDENCE_FOCUS_FRAMES],
                [0, 1],
                { ...CLAMP, easing: easeOut },
              );
              return (
                <div
                  key={`${i}-${pair.label}`}
                  style={{
                    display: 'flex',
                    alignItems: 'baseline',
                    gap: 16,

                    fontSize: SIZE.micro,
                    color: COLORS.textMuted,
                  }}
                >
                  <span
                    style={{
                      width: 12,
                      height: 12,
                      borderRadius: RADIUS.pill,
                      backgroundColor: COLORS.accent,
                      boxShadow: SHADOW.glow,
                      opacity: dotOpacity,
                    }}
                  />
                  <span>{pair.label}</span>
                  <span
                    style={{
                      fontFamily: FONT.mono,
                      fontSize: SIZE.small,
                      fontWeight: conflict ? WEIGHT.semibold : WEIGHT.regular,
                      color: conflict ? COLORS.accent : COLORS.textDim,
                    }}
                  >
                    {pair.ref}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </AbsoluteFill>
    </SceneStage>
  );
};