import type { ShowEventHistoryForm } from '@/modules/history/management/forms/form-types';
import type {
  PullEthBlockEventPayload,
  PullEvmTransactionPayload,
} from '@/types/history/events';

export interface HistoryEventsTableEmits {
  'show:form': [payload: ShowEventHistoryForm];
  'set-page': [page: number];
  'refresh': [payload?: PullEvmTransactionPayload];
  'refresh:block-event': [payload: PullEthBlockEventPayload];
}

export type HistoryEventsTableEmitFn = <K extends keyof HistoryEventsTableEmits>(
  event: K,
  ...args: HistoryEventsTableEmits[K]
) => void;
