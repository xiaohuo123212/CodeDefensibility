import React from 'react';
import {AbsoluteFill, Audio, Sequence, staticFile} from 'remotion';
import {Backdrop} from './components/Backdrop';
import {Subtitles} from './components/Subtitles';
import narrationJson from './data/narration.json';
import {S1Title} from './scenes/S1Title';
import {S2Terminal} from './scenes/S2Terminal';
import {S3Precheck} from './scenes/S3Precheck';
import {S4Trace} from './scenes/S4Trace';
import {S5Contra} from './scenes/S5Contra';
import {S6Metrics} from './scenes/S6Metrics';
import {S7Outro} from './scenes/S7Outro';
import {SCENES} from './timeline';
import type {Narration, SceneId, SceneProps} from './types';

const narration = narrationJson as unknown as Narration;

const SCENE_COMPONENTS: Array<{id: SceneId; component: React.FC<SceneProps>}> = [
  {id: 'S1', component: S1Title},
  {id: 'S2', component: S2Terminal},
  {id: 'S3', component: S3Precheck},
  {id: 'S4', component: S4Trace},
  {id: 'S5', component: S5Contra},
  {id: 'S6', component: S6Metrics},
  {id: 'S7', component: S7Outro},
];

export const Video: React.FC = () => {
  return (
    <AbsoluteFill>
      <Backdrop />
      {SCENE_COMPONENTS.map(({id, component: SceneComponent}) => {
        const range = SCENES[id];
        return (
          <Sequence
            key={id}
            name={id}
            from={range.start}
            durationInFrames={range.end - range.start}
          >
            <SceneComponent narration={narration} range={range} />
          </Sequence>
        );
      })}
      {/* 撤掉人声旁白，全片只留一条轻柔背景音乐（scripts/make_music.py 生成） */}
      <Audio src={staticFile('audio/bgm.wav')} volume={0.55} />
      <Subtitles narration={narration} />
    </AbsoluteFill>
  );
};