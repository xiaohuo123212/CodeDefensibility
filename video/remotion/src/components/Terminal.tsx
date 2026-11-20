import React from 'react';
import { useCurrentFrame } from 'remotion';
import { COLORS, FONT, MOTION, RADIUS, SHADOW, SIZE, WEIGHT } from '../theme';

export type TerminalLineKind = 'cmd' | 'out' | 'err';

export type TerminalLine = {
  text: string;
  kind: TerminalLineKind;
};

export type TerminalProps = {
  /** 窗框标题，取数据里的真实 cwd / 报告名，不另造文案 */
  title?: string;
  prompt: string;
  lines: TerminalLine[];
  /** 累计已打出的字符数（不含 prompt），用于逐字显示 */
  typedChars: number;
};

const TEXT_COLORS: Record<TerminalLineKind, string> = {
  cmd: COLORS.termCmd,
  out: COLORS.termOut,
  err: COLORS.termErr,
};

const CURSOR_BLINK_FRAMES = MOTION.cursorBlink;

const containerStyle: React.CSSProperties = {
  width: '100%',
  borderRadius: RADIUS.card,
  border: `1px solid ${COLORS.termBorder}`,
  backgroundColor: COLORS.termBg,
  boxShadow: SHADOW.card,
  overflow: 'hidden',
  fontFamily: FONT.mono,
  fontSize: SIZE.small,
  lineHeight: 1.75,
};

const headerStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 10,
  height: 46,
  padding: '0 22px',
  backgroundColor: COLORS.raise,
  borderBottom: `1px solid ${COLORS.line}`,
};

const bodyStyle: React.CSSProperties = {
  padding: '34px 42px 38px',
  whiteSpace: 'pre-wrap',
  wordBreak: 'break-all',
};

export const Terminal: React.FC<TerminalProps> = ({ title, prompt, lines, typedChars }) => {
  const frame = useCurrentFrame();
  const cursorVisible = Math.floor(frame / CURSOR_BLINK_FRAMES) % 2 === 0;

  const rendered: { index: number; text: string; kind: TerminalLineKind }[] = [];
  let remaining = Math.max(0, typedChars);
  let activeIndex = -1;

  for (let index = 0; index < lines.length && activeIndex === -1; index += 1) {
    const line = lines[index];
    const shown = Math.min(line.text.length, remaining);
    remaining -= shown;
    rendered.push({ index, text: line.text.slice(0, shown), kind: line.kind });
    if (shown < line.text.length) {
      activeIndex = index;
    }
  }

  const cursorIndex = activeIndex === -1 ? rendered.length - 1 : activeIndex;

  return (
    <div style={containerStyle}>
      <div style={headerStyle}>
        {[0.9, 0.55, 0.3].map((opacity) => (
          <span
            key={opacity}
            style={{
              width: 10,
              height: 10,
              borderRadius: '50%',
              backgroundColor: COLORS.textDim,
              opacity,
            }}
          />
        ))}
        {title ? (
          <span
            style={{
              marginLeft: 12,
              fontSize: SIZE.micro,
              fontWeight: WEIGHT.regular,
              color: COLORS.textMuted,
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}
          >
            {title}
          </span>
        ) : null}
      </div>
      <div style={bodyStyle}>
        {rendered.map((row) => (
          <div key={row.index}>
            {row.kind === 'cmd' ? (
              <span style={{ color: COLORS.termPrompt, fontWeight: WEIGHT.semibold }}>{prompt} </span>
            ) : null}
            <span style={{ color: TEXT_COLORS[row.kind] }}>{row.text}</span>
            {row.index === cursorIndex && cursorVisible ? (
              <span style={{ color: COLORS.accent }}>▍</span>
            ) : null}
          </div>
        ))}
      </div>
    </div>
  );
};