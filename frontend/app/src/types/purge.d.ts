import { type Purgeable } from '@/services/session/types';

export interface PurgeParams {
  readonly source: Purgeable;
  readonly text: string;
}
