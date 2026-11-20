import type {FrameRange, SceneId} from './types';

export const FPS = 30;
export const WIDTH = 1920;
export const HEIGHT = 1080;
export const TOTAL_FRAMES = 5040;

export const SCENES: Record<SceneId, FrameRange> = {
  S1: {start: 0, end: 456},
  S2: {start: 456, end: 864},
  S3: {start: 864, end: 1284},
  S4: {start: 1284, end: 3324},
  S5: {start: 3324, end: 3864},
  S6: {start: 3864, end: 4524},
  S7: {start: 4524, end: 5040},
};

export type S4PartId = 'S4a' | 'S4b' | 'S4c' | 'S4d';

export const S4PARTS: Record<S4PartId, FrameRange> = {
  S4a: {start: 1284, end: 1764},
  S4b: {start: 1764, end: 2244},
  S4c: {start: 2244, end: 2784},
  S4d: {start: 2784, end: 3324},
};

export const SCENE_ORDER: SceneId[] = ['S1', 'S2', 'S3', 'S4', 'S5', 'S6', 'S7'];