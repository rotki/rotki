import type { DialogShowOptions } from '@/components/history/events/dialog-types';
import type {
  PullEthBlockEventPayload,
  PullEvmTransactionPayload,
} from '@/types/history/events';

export interface HistoryEventsTableEmits {
  'show:dialog': [options: DialogShowOptions];
  'set-page': [page: number];
  'refresh': [payload?: PullEvmTransactionPayload];
  'refresh:block-event': [payload: PullEthBlockEventPayload];
}

export type HistoryEventsTableEmitFn = <K extends keyof HistoryEventsTableEmits>(
  event: K,
  ...args: HistoryEventsTableEmits[K]
) => void;
