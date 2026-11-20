import React from 'react';
import { COLORS, FONT, RADIUS, SIZE, WEIGHT } from '../theme';

export type ReportLineKind = 'title' | 'heading' | 'label' | 'item' | 'body' | 'meta';

export type ReportLine = {
  id: string;
  text: string;
  kind?: ReportLineKind;
};

export type ReportRow = {
  key: string;
  text: string;
  kind?: ReportLineKind;
  lineId: string;
  continuation: boolean;
};

export type ReportViewProps = {
  lines: ReportLine[];
  width?: number;
  height: number;
  lineHeight: number;
  fontSize: number;
  /** 单行最大字符数；超出部分折成续行，避免长句溢出画面 */
  charsPerLine: number;
  /** 已滚过的视觉行数（可为小数），0 表示顶部 */
  scrollLines?: number;
  /** lineId -> 0..1 的高亮强度 */
  highlight?: Record<string, number>;
  opacity?: number;
  /** 上下渐隐遮罩的底色，须与所在卡片表面一致 */
  surface?: string;
};

const MONO = FONT.mono;

/** 上下渐隐高度，保证滚到边缘的行不硬切。 */
const EDGE_FADE = 56;

const wrapText = (text: string, charsPerLine: number): string[] => {
  const chunks: string[] = [];
  let current = '';
  for (const ch of text) {
    if (current.length >= charsPerLine) {
      chunks.push(current);
      current = '';
    }
    current += ch;
  }
  if (current.length > 0) chunks.push(current);
  return chunks.length > 0 ? chunks : [''];
};

/** 把报告行按显示宽度铺成视觉行，返回视觉行与「lineId -> 首视觉行索引」映射。 */
export const layoutReport = (lines: ReportLine[], charsPerLine: number) => {
  const rows: ReportRow[] = [];
  const index: Record<string, number> = {};
  for (const line of lines) {
    index[line.id] = rows.length;
    wrapText(line.text, charsPerLine).forEach((text, i) => {
      rows.push({ key: `${line.id}#${i}`, text, kind: line.kind, lineId: line.id, continuation: i > 0 });
    });
  }
  return { rows, index };
};

const kindStyle = (kind: ReportLineKind | undefined, fontSize: number): React.CSSProperties => {
  switch (kind) {
    case 'title':
      return { fontSize: SIZE.small, fontWeight: WEIGHT.bold, color: COLORS.text };
    case 'heading':
      return { fontSize: SIZE.small, fontWeight: WEIGHT.semibold, color: COLORS.accent };
    case 'label':
      return { fontSize, fontWeight: WEIGHT.semibold, color: COLORS.accent };
    case 'item':
      return { fontSize, fontWeight: WEIGHT.regular, color: COLORS.textBody };
    case 'meta':
      return { fontSize: SIZE.micro, fontWeight: WEIGHT.regular, color: COLORS.textMuted };
    case 'body':
    default:
      return { fontSize, fontWeight: WEIGHT.regular, color: COLORS.text };
  }
};

const kindIndent = (kind: ReportLineKind | undefined): number => (kind === 'item' ? 26 : 0);

export const ReportView: React.FC<ReportViewProps> = ({
  lines,
  width,
  height,
  lineHeight,
  fontSize,
  charsPerLine,
  scrollLines = 0,
  highlight,
  opacity = 1,
  surface = COLORS.raise,
}) => {
  const { rows } = layoutReport(lines, charsPerLine);

  return (
    <div
      style={{
        position: 'relative',
        width,
        height,
        overflow: 'hidden',
        opacity,
        fontFamily: MONO,
        fontSize,
        lineHeight: `${lineHeight}px`,
      }}
    >
      <div style={{ transform: `translateY(${-scrollLines * lineHeight}px)` }}>
        {rows.map((row) => {
          const strength = (highlight?.[row.lineId] ?? 0) * (row.continuation ? 0.7 : 1);
          return (
            <div
              key={row.key}
              style={{
                position: 'relative',
                height: lineHeight,
                display: 'flex',
                alignItems: 'center',
                paddingLeft: 30 + kindIndent(row.kind) + (row.continuation ? kindIndent(row.kind) : 0),
                paddingRight: 30,
                whiteSpace: 'nowrap',
              }}
            >
              {strength > 0.001 ? (
                <div
                  style={{
                    position: 'absolute',
                    left: 4,
                    right: 4,
                    top: 3,
                    bottom: 3,
                    borderRadius: RADIUS.sm,
                    background: COLORS.accentDim,
                    borderLeft: `3px solid ${COLORS.accent}`,
                    opacity: strength,
                  }}
                />
              ) : null}
              <span style={{ position: 'relative', ...kindStyle(row.kind, fontSize) }}>{row.text}</span>
            </div>
          );
        })}
      </div>

      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          height: EDGE_FADE,
          background: `linear-gradient(to bottom, ${surface}, transparent)`,
          pointerEvents: 'none',
        }}
      />
      <div
        style={{
          position: 'absolute',
          bottom: 0,
          left: 0,
          right: 0,
          height: EDGE_FADE,
          background: `linear-gradient(to top, ${surface}, transparent)`,
          pointerEvents: 'none',
        }}
      />
    </div>
  );
};