import React from 'react';
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from 'remotion';
import type { SceneProps } from '../types';
import { SceneStage } from '../components/SceneStage';
import { Terminal, TerminalLine } from '../components/Terminal';
import { COLORS, LAYOUT, RADIUS } from '../theme';
import terminalJson from '../data/terminal.json';

const CLAMP = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' } as const;
const PANEL_WIDTH = 1440;
const LEAD_FRAMES = 30;
const FRAMES_PER_CHAR = 1.5;
const LINE_PAUSE_FRAMES = 30;

/** C-V09：outputs 行出现时边框 6 帧内提亮一档，再 14 帧回落。 */
const BORDER_BOOST_UP = 6;
const BORDER_BOOST_DOWN = 14;

/** C-V09：结束前 30 帧，标题栏第一个圆点做一次 accent 闪烁。 */
const DOT_FLASH_LEAD = 30;
const DOT_FLASH_FRAMES = 12;

/** Terminal 标题栏的内边距与圆点尺寸，用于把 accent 圆点对齐到第一个圆点。 */
const HEADER_PAD_X = 22;
const HEADER_HEIGHT = 46;
const DOT_SIZE = 10;

type TerminalOutput = { text: string; kind: string };

type TerminalData = {
  ready: boolean;
  cwd: string;
  prompt: string;
  commandLine: string;
  outputs: TerminalOutput[];
  exitCode: number;
  reportPath: string;
  capturedAt: string;
};

const terminalData = terminalJson as TerminalData;

const toTerminalLine = (output: TerminalOutput): TerminalLine => ({
  text: output.text,
  kind: output.kind === 'err' ? 'err' : 'out',
});

// cd 的目标目录取自 C-006 的 cwd，不另写死路径
const buildLines = (data: TerminalData): TerminalLine[] => [
  { text: `cd ${data.cwd}`, kind: 'cmd' },
  { text: data.commandLine, kind: 'cmd' },
  ...data.outputs.map(toTerminalLine),
];

const typedCharsAt = (lines: TerminalLine[], frame: number): number => {
  let remainingFrames = frame - LEAD_FRAMES;
  let typed = 0;

  for (const line of lines) {
    if (remainingFrames < 0) {
      break;
    }
    const chars = Math.min(line.text.length, Math.floor(remainingFrames / FRAMES_PER_CHAR));
    typed += chars;
    remainingFrames -= chars * FRAMES_PER_CHAR;
    if (chars < line.text.length) {
      break;
    }
    remainingFrames -= LINE_PAUSE_FRAMES;
  }

  return typed;
};

/** 每行开始打字的帧，与 typedCharsAt 的节奏保持一致。 */
const lineStartFrames = (lines: TerminalLine[]): number[] => {
  const starts: number[] = [];
  let cursor = LEAD_FRAMES;
  for (const line of lines) {
    starts.push(cursor);
    cursor += line.text.length * FRAMES_PER_CHAR + LINE_PAUSE_FRAMES;
  }
  return starts;
};

export const S2Terminal: React.FC<SceneProps> = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const lines = buildLines(terminalData);

  const starts = lineStartFrames(lines);
  const outputsStart = starts[2] ?? null;
  const borderBoost =
    outputsStart === null
      ? 0
      : interpolate(
          frame,
          [outputsStart, outputsStart + BORDER_BOOST_UP, outputsStart + BORDER_BOOST_UP + BORDER_BOOST_DOWN],
          [0, 1, 0],
          CLAMP,
        );

  const dotFlashStart = durationInFrames - DOT_FLASH_LEAD;
  const dotFlash = interpolate(
    frame,
    [dotFlashStart, dotFlashStart + DOT_FLASH_FRAMES / 2, dotFlashStart + DOT_FLASH_FRAMES],
    [0, 1, 0],
    CLAMP,
  );

  return (
    <SceneStage scene="S2">
      <AbsoluteFill
        style={{
          alignItems: 'center',
          justifyContent: 'center',
          paddingTop: LAYOUT.padY,
          paddingBottom: 200,
          paddingLeft: LAYOUT.padX,
          paddingRight: LAYOUT.padX,
        }}
      >
        <div style={{ width: PANEL_WIDTH, position: 'relative' }}>
          <Terminal
            title={terminalData.cwd}
            prompt={terminalData.prompt}
            lines={lines}
            typedChars={typedCharsAt(lines, frame)}
          />
          <div
            style={{
              position: 'absolute',
              inset: 0,
              borderRadius: RADIUS.card,
              border: `1px solid ${COLORS.accent}`,
              boxShadow: `0 0 28px ${COLORS.accentGlow}`,
              opacity: borderBoost,
              pointerEvents: 'none',
            }}
          />
          <div
            style={{
              position: 'absolute',
              left: HEADER_PAD_X,
              top: (HEADER_HEIGHT - DOT_SIZE) / 2,
              width: DOT_SIZE,
              height: DOT_SIZE,
              borderRadius: '50%',
              backgroundColor: COLORS.accent,
              opacity: dotFlash,
              pointerEvents: 'none',
            }}
          />
        </div>
      </AbsoluteFill>
    </SceneStage>
  );
};