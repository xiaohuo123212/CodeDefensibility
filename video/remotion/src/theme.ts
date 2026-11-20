/**
 * 全片唯一的视觉令牌来源（C-V01）。
 *
 * 任何 scene / component 都不得自写魔法色值或字号：
 * 需要新颜色就先在这里登记，否则视为违约。
 */

export const COLORS = {
  // 背景层（Backdrop 使用，场景一律透明）
  bgTop: '#070A0E',
  bgMid: '#0B0F14',
  bgBottom: '#05070A',
  // 抬升面（卡片、终端、说明条）
  raise: '#111A24',
  raiseSoft: 'rgba(17,26,36,0.86)',
  // 分隔线与描边
  line: '#1E2A36',
  lineSoft: 'rgba(255,255,255,0.06)',
  // 文字层级
  text: '#F2F5F8',
  textBody: '#D5DEE7',
  textMuted: '#9AABBC',
  textDim: '#667687',
  // 单点强调色（与 PPT 视觉系统一致），只用于关键词、序号、光标
  accent: '#21B8C7',
  accentDim: 'rgba(33,184,199,0.16)',
  accentGlow: 'rgba(33,184,199,0.32)',
  // 语义色
  ok: '#4ADE80',
  warn: '#F0C24B',
  danger: '#FF7A70',
  // 终端
  termBg: '#080C12',
  termBorder: '#1A2530',
  termPrompt: '#3FB950',
  termCmd: '#E6EDF3',
  termOut: '#7EE787',
  termErr: '#FF7B72',
} as const;

/** 本机无 MiSans / Didot，一律用系统可用的等价栈，禁止引用未安装字体。 */
export const FONT = {
  sans: "'Microsoft YaHei', 'PingFang SC', 'Noto Sans SC', 'Segoe UI', sans-serif",
  mono: "'Cascadia Code', 'JetBrains Mono', Consolas, 'Courier New', monospace",
} as const;

/**
 * 字号阶梯（1080p 逻辑像素）。
 * 安全宽度：单行中文宽度 ≈ 字数 × 字号 ≤ 1600px，超了必须换行或降一档。
 */
export const SIZE = {
  hero: 104,
  title: 68,
  headline: 52,
  body: 38,
  small: 28,
  micro: 22,
} as const;

export const WEIGHT = {
  bold: 700,
  semibold: 600,
  medium: 500,
  regular: 400,
} as const;

export const RADIUS = {
  card: 18,
  panel: 14,
  sm: 8,
  pill: 999,
} as const;

export const SHADOW = {
  card: '0 30px 90px rgba(0,0,0,0.55)',
  cardSoft: '0 18px 50px rgba(0,0,0,0.42)',
  glow: '0 0 0 1px rgba(33,184,199,0.28), 0 0 40px rgba(33,184,199,0.16)',
  text: '0 2px 18px rgba(0,0,0,0.88)',
  textSoft: '0 2px 10px rgba(0,0,0,0.72)',
} as const;

/** 版面栅格：左右安全边距 120px → 内容宽 1680px，正文块建议 ≤1600px。 */
export const LAYOUT = {
  padX: 120,
  padY: 88,
  safeWidth: 1600,
  subtitleBottom: 76,
} as const;

/** 动效节奏（帧，30fps）。 */
export const MOTION = {
  fade: 18,
  rise: 16,
  stagger: 6,
  cursorBlink: 15,
} as const;

/** 与 Remotion interpolate 的 easing 选项兼容的三次缓出。 */
export const easeOut = (t: number): number => 1 - Math.pow(1 - t, 3);

/** 缓入缓出，用于位移较大的转场。 */
export const easeInOut = (t: number): number =>
  t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;