import { SuggestedReply } from './types';

export const API_TIMEOUT_MS = 30000;
export const CHAT_TIMEOUT_MS = 60000;

export const STARTER_CHIPS: SuggestedReply[] = [
  { id: 'engine_no_crank', label: "Car won't start", question_id: 'intake' },
  { id: 'brake_squeal', label: 'Brake noise', question_id: 'intake' },
  { id: 'overheating', label: 'Overheating', question_id: 'intake' },
  { id: 'check_engine_light', label: 'Warning light on', question_id: 'intake' },
  { id: 'vibration_speed', label: 'Vibration / shaking', question_id: 'intake' },
  { id: 'ac_not_cooling', label: 'AC not cooling', question_id: 'intake' },
];

export const MAX_IMAGE_SIZE = 5 * 1024 * 1024;
export const MAX_AUDIO_SIZE = 10 * 1024 * 1024;
export const MAX_VIDEO_SIZE = 20 * 1024 * 1024;

export const STORAGE_CONV_IDS = 'cm:convs';
export const STORAGE_ACTIVE = 'cm:active';
