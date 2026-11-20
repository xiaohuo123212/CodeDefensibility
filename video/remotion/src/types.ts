export type SceneId = 'S1' | 'S2' | 'S3' | 'S4' | 'S5' | 'S6' | 'S7';

export type SentenceSceneId = SceneId;

export type NarrationSentence = {
  id: number;
  no: string;
  scene: SentenceSceneId;
  text: string;
  audioFile: string;
  durationMs: number;
  startFrame: number;
  endFrame: number;
  audioSha256?: string;
};

export type NarrationScene = {
  id: SceneId;
  startFrame: number;
  endFrame: number;
  sentenceIds: number[];
};

/** C-001：narration.json 的完整结构，消费者只读不改。 */
export type Narration = {
  fps: number;
  totalFrames: number;
  voice: string;
  fit: boolean;
  warnings: string[];
  /** 画面文案（非旁白），逐字取自 video/视频稿.md 第四节字幕清单。 */
  s1Titles?: [string, string];
  s7Outro?: string;
  sentences: NarrationSentence[];
  scenes: NarrationScene[];
};

export type FrameRange = {
  start: number;
  end: number;
};

/** C-007：所有 scene 组件的统一签名。 */
export type SceneProps = {
  narration: Narration;
  range: FrameRange;
};