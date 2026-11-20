import React from 'react';
import { interpolate, useCurrentFrame } from 'remotion';
import type { SceneProps } from '../types';
import { S4PARTS } from '../timeline';
import { ReportView, layoutReport, type ReportLine } from '../components/ReportView';
import { SceneStage } from '../components/SceneStage';
import { ScanSweep } from '../components/ScanSweep';
import { COLORS, FONT, LAYOUT, MOTION, RADIUS, SHADOW, SIZE, WEIGHT, easeOut } from '../theme';
import spec from '../data/report-fx-spec.json';

const CLAMP = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' } as const;

type SpecItem = (typeof spec.items)[number];
type PartKey = 'S4a' | 'S4b' | 'S4c' | 'S4d';

const RAIL_WIDTH = 260;
const GAP = 36;
const PANEL_WIDTH = LAYOUT.safeWidth - RAIL_WIDTH - GAP;
const BODY_HEIGHT = 600;
const PANEL_PAD = 36;
const PANEL_HEADER = 46;
const LINE_HEIGHT = Math.round(SIZE.small * 1.9);
const REPORT_HEIGHT = BODY_HEIGHT - PANEL_PAD * 2 - PANEL_HEADER;
const VISIBLE_ROWS = Math.max(1, Math.floor(REPORT_HEIGHT / LINE_HEIGHT));
const CHARS_PER_LINE = 62;

// 左栏：4 段进度 + 6 个探测槽位，两段加起来刚好放进 BODY_HEIGHT。
const SEG_HEIGHT = 70;
const SEG_GAP = 8;
const RAIL_GAP = 14;
const SLOT_HEIGHT = 42;
const SLOT_GAP = 4;
const BAND_HEIGHT = 46;

/** S4d 只留结论时，其余内容的压暗值（C-V09）。 */
const DIM_OPACITY = 0.35;

// 本段讲的是「没找到证据」里清单最长的那一条；没有「没找到」条目时退回首条。
const pickFocusItem = (): SpecItem => {
  const missingPool = spec.items.filter((item) => item.conclusion.includes('没找到'));
  const pool = missingPool.length > 0 ? missingPool : spec.items;
  return pool.reduce((best, item) => (item.missing.length > best.missing.length ? item : best));
};

const focusItem = pickFocusItem();

const LINES: ReportLine[] = (() => {
  const lines: ReportLine[] = [
    { id: 'item-title', text: focusItem.title, kind: 'title' },
    { id: 'source', text: `来源：${focusItem.sourceLine}`, kind: 'meta' },
  ];

  if (focusItem.found.length > 0) {
    lines.push({ id: 'found-head', text: '查到：', kind: 'label' });
    focusItem.found.forEach((found, i) => {
      lines.push({ id: `found-${i}`, text: `${found.type}：${found.count} 处`, kind: 'item' });
    });
  }

  lines.push({ id: 'missing-head', text: '查过没找到：', kind: 'label' });
  focusItem.missing.forEach((missing, i) => {
    lines.push({
      id: `missing-${i}`,
      text: `${missing.type}：${missing.count} 处（扫过 ${missing.scanned} 处）`,
      kind: 'item',
    });
  });

  lines.push({ id: 'conclusion', text: `结论：${focusItem.conclusion}`, kind: 'body' });
  if (focusItem.hypothesis) {
    lines.push({ id: 'hypothesis', text: focusItem.hypothesis, kind: 'body' });
  }
  lines.push({ id: 'question', text: `会被问：${focusItem.question}`, kind: 'body' });
  lines.push({ id: 'todo', text: `该补什么：${focusItem.todo}`, kind: 'body' });
  lines.push({ id: 'criteria', text: `判据：${focusItem.criteria}`, kind: 'body' });
  lines.push({ id: 'audit', text: `audit effort：${focusItem.auditEffort}`, kind: 'body' });

  return lines;
})();

const MISSING_IDS = focusItem.missing.map((_, i) => `missing-${i}`);
const { rows: ROWS, index: ROW_INDEX } = layoutReport(LINES, CHARS_PER_LINE);
const MAX_SCROLL = Math.max(0, ROWS.length - VISIBLE_ROWS);
const SLOT_AREA_HEIGHT =
  focusItem.missing.length * SLOT_HEIGHT + Math.max(0, focusItem.missing.length - 1) * SLOT_GAP;

const center = (id: string) =>
  Math.min(MAX_SCROLL, Math.max(0, (ROW_INDEX[id] ?? 0) - VISIBLE_ROWS / 2));

const PARTS: { key: PartKey; no: string; label: string }[] = [
  { key: 'S4a', no: '01', label: '查过哪里' },
  { key: 'S4b', no: '02', label: '换过假设' },
  { key: 'S4c', no: '03', label: '判据来源' },
  { key: 'S4d', no: '04', label: '该补什么' },
];

export const S4Trace: React.FC<SceneProps> = ({ range }) => {
  const frame = useCurrentFrame();

  // S4PARTS 按设计表为绝对帧；若上游给的是 S4 内相对帧，也照常可用。
  const part = (key: PartKey) => {
    const bounds = (S4PARTS as Record<string, { start: number; end: number }>)[key];
    const absolute = bounds.start >= range.start && bounds.end <= range.end;
    return absolute
      ? { start: bounds.start - range.start, end: bounds.end - range.start }
      : { start: bounds.start, end: bounds.end };
  };

  const a = part('S4a');
  const b = part('S4b');
  const c = part('S4c');
  const d = part('S4d');
  const dLength = d.end - d.start;

  const at = (from: number, to: number, outFrom: number, outTo: number) =>
    interpolate(frame, [from, to], [outFrom, outTo], { ...CLAMP, easing: easeOut });

  let scroll = at(a.start + 20, a.start + 150, 0, center('missing-head'));
  if (frame >= b.start) scroll = at(b.start, b.start + 120, center('missing-head'), center('hypothesis'));
  if (frame >= b.start + 220) scroll = at(b.start + 220, b.start + 350, center('hypothesis'), center('audit'));
  if (frame >= c.start) scroll = at(c.start, c.start + 140, center('audit'), center('criteria'));
  if (frame >= c.start + 260) scroll = at(c.start + 260, c.start + 390, center('criteria'), center('todo'));
  if (frame >= d.start) scroll = at(d.start, d.start + dLength * 0.55, 0, MAX_SCROLL);

  // 槽位点亮进度：S4a 两次扫描各点亮一半，扫到即亮并保留（跨段累积）。
  const half = Math.ceil(focusItem.missing.length / 2);
  const scanOnce = at(a.start + 80, a.start + 230, 0, 1);
  const scanTwice = at(a.start + 280, a.start + 440, 0, 1);
  const litByScan = (i: number): number => {
    const local =
      i < half
        ? scanOnce * half - i
        : scanTwice * (focusItem.missing.length - half) - (i - half);
    return Math.min(1, Math.max(0, local));
  };

  // S4b 换假设：槽位全部回到灰态，只让第一项短暂亮起后熄灭。
  const pulse = at(b.start + 240, b.start + 320, 0, 1) * (1 - at(b.start + 340, b.start + 400, 0, 1));
  const slotLit = (i: number): number => {
    if (frame >= b.start) return frame < b.end && i === 0 ? pulse : 0;
    return litByScan(i);
  };

  // 点亮后一直保持，轨迹逐段累积而不是来回切换。
  const highlight: Record<string, number> = {};
  const mark = (id: string, value: number) => {
    if (value > 0.001) highlight[id] = Math.max(highlight[id] ?? 0, value);
  };

  mark('missing-head', at(a.start + 40, a.start + 80, 0, 1));
  MISSING_IDS.forEach((id, i) => mark(id, litByScan(i)));
  mark('hypothesis', at(b.start + 100, b.start + 170, 0, 1));
  mark('audit', at(b.start + 320, b.start + 390, 0, 1));
  mark('criteria', at(c.start + 120, c.start + 200, 0, 1));
  mark('todo', at(c.start + 360, c.start + 450, 0, 1));
  mark('conclusion', at(d.start + 40, d.start + 160, 0, 1));

  const activeIndex =
    frame >= d.start ? 3 : frame >= c.start ? 2 : frame >= b.start ? 1 : 0;
  const dimmed = at(d.start, d.start + 24, 0, 1);
  const restOpacity = 1 - (1 - DIM_OPACITY) * dimmed;
  const hollow = frame >= d.start;
  const critIn = at(c.start + 120, c.start + 200, 0, 1);
  const leadIn = at(d.start + dLength * 0.3, d.start + dLength * 0.45, 0, 1);
  const headIn = at(0, MOTION.fade, 0, 1);

  return (
    <SceneStage scene="S4">
      <div
        style={{
          width: '100%',
          height: '100%',
          boxSizing: 'border-box',
          paddingLeft: LAYOUT.padX,
          paddingRight: LAYOUT.padX,
          paddingTop: LAYOUT.padY,
          fontFamily: FONT.sans,
        }}
      >
        <div
          style={{
            width: LAYOUT.safeWidth,
            display: 'flex',
            alignItems: 'baseline',
            justifyContent: 'space-between',
            opacity: headIn * restOpacity,
            transform: `translateY(${(1 - headIn) * MOTION.rise}px)`,
          }}
        >
          <div style={{ fontSize: SIZE.headline, fontWeight: WEIGHT.semibold, color: COLORS.text }}>
            {spec.title}
          </div>
          <div style={{ fontFamily: FONT.mono, fontSize: SIZE.micro, color: COLORS.textMuted }}>
            {spec.sourceMd}
          </div>
        </div>

        <div style={{ display: 'flex', gap: GAP, marginTop: SIZE.small }}>
          <div
            style={{
              width: RAIL_WIDTH,
              height: BODY_HEIGHT,
              display: 'flex',
              flexDirection: 'column',
              opacity: restOpacity,
            }}
          >
            {PARTS.map((item, i) => {
              const reached = i <= activeIndex;
              const active = i === activeIndex;
              return (
                <div
                  key={item.key}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 18,
                    padding: '0 24px',
                    height: SEG_HEIGHT,
                    marginBottom: SEG_GAP,
                    borderRadius: RADIUS.panel,
                    background: active ? COLORS.accentDim : COLORS.raiseSoft,
                    border: `1px solid ${active ? COLORS.accent : COLORS.line}`,
                    boxShadow: active ? SHADOW.glow : 'none',
                    opacity: reached ? 1 : 0.55,
                  }}
                >
                  <div
                    style={{
                      fontFamily: FONT.mono,
                      fontSize: SIZE.small,
                      fontWeight: WEIGHT.semibold,
                      color: reached ? COLORS.accent : COLORS.textDim,
                    }}
                  >
                    {item.no}
                  </div>
                  <div
                    style={{
                      fontSize: SIZE.small,
                      fontWeight: active ? WEIGHT.semibold : WEIGHT.medium,
                      color: active ? COLORS.text : COLORS.textMuted,
                    }}
                  >
                    {item.label}
                  </div>
                </div>
              );
            })}

            <div
              style={{
                position: 'relative',
                marginTop: RAIL_GAP - SEG_GAP,
                height: SLOT_AREA_HEIGHT,
                overflow: 'hidden',
                display: 'flex',
                flexDirection: 'column',
                gap: SLOT_GAP,
              }}
            >
              {focusItem.missing.map((missing, i) => {
                const lit = slotLit(i);
                const on = lit > 0.5;
                return (
                  <div
                    key={`${missing.type}-${i}`}
                    style={{
                      height: SLOT_HEIGHT,
                      flex: 'none',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 10,
                      padding: '0 14px',
                      borderRadius: RADIUS.sm,
                      border: `1px solid ${on && !hollow ? COLORS.accent : COLORS.line}`,
                      background: hollow ? 'transparent' : on ? COLORS.accentDim : COLORS.raiseSoft,
                      boxSizing: 'border-box',
                    }}
                  >
                    <div
                      style={{
                        width: 16,
                        height: 16,
                        flex: 'none',
                        borderRadius: hollow ? RADIUS.pill : RADIUS.sm,
                        border: `2px solid ${hollow ? COLORS.textDim : on ? COLORS.accent : COLORS.line}`,
                        background: hollow || !on ? 'transparent' : COLORS.accent,
                        boxSizing: 'border-box',
                      }}
                    />
                    <span
                      style={{
                        fontSize: SIZE.micro,
                        fontWeight: on && !hollow ? WEIGHT.semibold : WEIGHT.regular,
                        color: hollow ? COLORS.textDim : on ? COLORS.text : COLORS.textMuted,
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {missing.type}
                    </span>
                  </div>
                );
              })}

              <ScanSweep from={a.start + 80} to={a.start + 230} height={BAND_HEIGHT} />
              <ScanSweep from={a.start + 280} to={a.start + 440} height={BAND_HEIGHT} />
              <ScanSweep from={b.start + 60} to={b.start + 200} height={BAND_HEIGHT} />
            </div>
          </div>

          <div
            style={{
              position: 'relative',
              width: PANEL_WIDTH,
              height: BODY_HEIGHT,
              padding: PANEL_PAD,
              borderRadius: RADIUS.card,
              background: COLORS.raise,
              border: `1px solid ${COLORS.line}`,
              boxShadow: SHADOW.card,
              overflow: 'hidden',
              boxSizing: 'border-box',
              opacity: restOpacity,
            }}
          >
            <div
              style={{
                height: PANEL_HEADER,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                fontSize: SIZE.micro,
                color: COLORS.textDim,
              }}
            >
              <span>报告轨迹</span>
              <span style={{ fontFamily: FONT.mono }}>{`${focusItem.missing.length} 处未找到`}</span>
            </div>
            <ReportView
              lines={LINES}
              width={PANEL_WIDTH - PANEL_PAD * 2}
              height={REPORT_HEIGHT}
              lineHeight={LINE_HEIGHT}
              fontSize={SIZE.small}
              charsPerLine={CHARS_PER_LINE}
              scrollLines={scroll}
              highlight={highlight}
              surface={COLORS.raise}
            />

            {/* S4c：判据行从卡片下沿上浮落位 */}
            <div
              style={{
                position: 'absolute',
                left: PANEL_PAD,
                right: PANEL_PAD,
                bottom: PANEL_PAD,
                minHeight: 76,
                boxSizing: 'border-box',
                display: 'flex',
                alignItems: 'center',
                gap: 16,
                padding: '0 24px',
                borderRadius: RADIUS.sm,
                background: COLORS.raiseSoft,
                border: `1px solid ${COLORS.line}`,
                borderLeft: `3px solid ${COLORS.accent}`,
                fontSize: SIZE.small,
                fontWeight: WEIGHT.medium,
                color: COLORS.textBody,
                opacity: critIn,
                transform: `translateY(${(1 - critIn) * 20}px)`,
              }}
            >
              判据：{focusItem.criteria}
            </div>
          </div>
        </div>

        <div
          style={{
            width: LAYOUT.safeWidth,
            marginTop: SIZE.small,
            minHeight: 92,
            display: 'flex',
            alignItems: 'center',
            gap: 24,
            padding: '0 32px',
            borderRadius: RADIUS.panel,
            background: COLORS.raiseSoft,
            border: `1px solid ${COLORS.line}`,
            borderLeft: `3px solid ${COLORS.accent}`,
            opacity: leadIn,
            transform: `translateY(${(1 - leadIn) * MOTION.rise}px)`,
          }}
        >
          <div style={{ fontSize: SIZE.body, fontWeight: WEIGHT.medium, color: COLORS.text }}>
            {spec.lead}
          </div>
        </div>
      </div>
    </SceneStage>
  );
};