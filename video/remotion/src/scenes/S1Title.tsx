import React from 'react';
import { AbsoluteFill, interpolate, useCurrentFrame } from 'remotion';
import type { SceneProps } from '../types';
import { SceneStage } from '../components/SceneStage';
import { COLORS, FONT, LAYOUT, MOTION, SIZE, WEIGHT, easeInOut, easeOut } from '../theme';

const CLAMP = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' } as const;

/** 两行标题的主次：主问句大，补充句降档降色，建立字号层级。 */
const TITLE_LEVELS = [
  { fontSize: SIZE.hero, color: COLORS.text, weight: WEIGHT.bold, marginTop: 40 },
  { fontSize: SIZE.headline, color: COLORS.textMuted, weight: WEIGHT.medium, marginTop: 36 },
];

/** C-V09：主标题遮罩揭示 18 帧，第二行相对第一行延后 20 帧。 */
const MASK_FRAMES = 18;
const SECOND_LINE_DELAY = 20;

/** C-V09：画面里一条极细光带在 60–150 帧之间横向扫过一次（仅一次）。 */
const SWEEP_FROM = 60;
const SWEEP_TO = 150;
const SWEEP_FADE = 12;
const SWEEP_WIDTH_PERCENT = 30;

/** 揭示完成后补上强调的关键词（文本本身仍全部取自 narration）。 */
const ACCENT_KEYWORD = '500 并发';

const hexToRgb = (hex: string): [number, number, number] => {
  const value = hex.replace('#', '');
  return [
    parseInt(value.slice(0, 2), 16),
    parseInt(value.slice(2, 4), 16),
    parseInt(value.slice(4, 6), 16),
  ];
};

/** 两个 theme 令牌之间线性混色，用于关键词从正文色过渡到强调色。 */
const mixColor = (from: string, to: string, t: number): string => {
  const a = hexToRgb(from);
  const b = hexToRgb(to);
  return `rgb(${a.map((channel, index) => Math.round(channel + (b[index] - channel) * t)).join(', ')})`;
};

const maskReveal = (frame: number, start: number): React.CSSProperties => {
  const progress = interpolate(frame, [start, start + MASK_FRAMES], [0, 1], {
    ...CLAMP,
    easing: easeOut,
  });
  return {
    clipPath: `inset(0 ${(1 - progress) * 100}% 0 0)`,
    transform: `translateY(${(1 - progress) * 10}px)`,
  };
};

const splitKeyword = (text: string, keyword: string) => {
  const at = text.indexOf(keyword);
  if (at < 0) {
    return { head: text, keyword: '', tail: '' };
  }
  return {
    head: text.slice(0, at),
    keyword,
    tail: text.slice(at + keyword.length),
  };
};

export const S1Title: React.FC<SceneProps> = ({ narration, range }) => {
  const frame = useCurrentFrame();

  const sentences = narration.sentences
    .filter((sentence) => sentence.scene === 'S1')
    .sort((a, b) => a.id - b.id);
  const texts =
    narration.s1Titles && narration.s1Titles.length > 0
      ? narration.s1Titles
      : sentences.map((sentence) => sentence.text);

  const titles = texts.slice(0, 2).map((text, index) => ({
    text,
    startFrame: sentences[index]?.startFrame ?? range.start,
    level: TITLE_LEVELS[index] ?? TITLE_LEVELS[TITLE_LEVELS.length - 1],
  }));

  const firstStart = Math.max(0, (titles[0]?.startFrame ?? range.start) - range.start);
  const secondStart = firstStart + SECOND_LINE_DELAY;
  const markerStart = firstStart;

  const firstLine = splitKeyword(titles[0]?.text ?? '', ACCENT_KEYWORD);
  const accentProgress = interpolate(
    frame,
    [firstStart + MASK_FRAMES, firstStart + MASK_FRAMES + MOTION.fade],
    [0, 1],
    { ...CLAMP, easing: easeOut },
  );

  const sweepProgress = interpolate(frame, [SWEEP_FROM, SWEEP_TO], [0, 1], {
    ...CLAMP,
    easing: easeInOut,
  });
  const sweepOpacity = interpolate(
    frame,
    [SWEEP_FROM, SWEEP_FROM + SWEEP_FADE, SWEEP_TO - SWEEP_FADE, SWEEP_TO],
    [0, 0.7, 0.7, 0],
    CLAMP,
  );

  return (
    <SceneStage scene="S1">
      <AbsoluteFill
        style={{
          alignItems: 'center',
          justifyContent: 'center',
          padding: `0 ${LAYOUT.padX}px`,
          fontFamily: FONT.sans,
        }}
      >
        <div
          style={{
            position: 'absolute',
            top: '46%',
            left: `${-SWEEP_WIDTH_PERCENT + sweepProgress * (100 + SWEEP_WIDTH_PERCENT)}%`,
            width: `${SWEEP_WIDTH_PERCENT}%`,
            height: 2,
            background: `linear-gradient(90deg, transparent, ${COLORS.accent}, transparent)`,
            opacity: sweepOpacity,
          }}
        />
        <div
          style={{
            maxWidth: LAYOUT.safeWidth,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            textAlign: 'center',
          }}
        >
          <div
            style={{
              width: 96,
              height: 4,
              borderRadius: 2,
              backgroundColor: COLORS.accent,
              ...maskReveal(frame, markerStart),
            }}
          />
          <div
            style={{
              marginTop: titles[0]?.level.marginTop,
              fontSize: titles[0]?.level.fontSize,
              fontWeight: titles[0]?.level.weight,
              color: titles[0]?.level.color,
              lineHeight: 1.28,
              ...maskReveal(frame, firstStart),
            }}
          >
            {firstLine.head}
            {firstLine.keyword ? (
              <span style={{ color: mixColor(COLORS.text, COLORS.accent, accentProgress) }}>
                {firstLine.keyword}
              </span>
            ) : null}
            {firstLine.tail}
          </div>
          {titles[1] ? (
            <div
              style={{
                marginTop: titles[1].level.marginTop,
                fontSize: titles[1].level.fontSize,
                fontWeight: titles[1].level.weight,
                color: titles[1].level.color,
                lineHeight: 1.28,
                ...maskReveal(frame, secondStart),
              }}
            >
              {titles[1].text}
            </div>
          ) : null}
        </div>
      </AbsoluteFill>
    </SceneStage>
  );
};