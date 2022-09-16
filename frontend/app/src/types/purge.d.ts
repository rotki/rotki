import { Purgeable } from '@/services/session/types';

export type PurgeParams = { readonly source: Purgeable; readonly text: string };
