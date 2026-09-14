import type { PaginationRequestPayload } from '@/modules/core/common/common-types';
import type { FilterObjectWithBehaviour } from '@/modules/core/table/filtering';
import type {
  AddEvmSwapEventPayload,
  AddSolanaSwapEventPayload,
  AddSwapEventPayload,
  EditEvmSwapEventPayload,
  EditHistoryEventPayload,
  EditSolanaSwapEventPayload,
  EditSwapEventPayload,
  NewHistoryEventPayload,
} from '@/modules/history/events/event-edit-payloads';

export interface HistoryEventRequestPayload extends PaginationRequestPayload<{ timestamp: number }> {
  readonly fromTimestamp?: string | number;
  readonly toTimestamp?: string | number;
  readonly aggregateByGroupIds: boolean;
  readonly groupIdentifiers?: string | string[];
  readonly eventTypes?: string | string[];
  readonly eventSubtypes?: string | string[];
  readonly locationLabels?: string | string[];
  readonly asset?: string;
  readonly counterparties?: string | string[];
  readonly location?: string | string[];
  readonly products?: string | string[];
  readonly entryTypes?: FilterObjectWithBehaviour<string | string[]>;
  readonly txHashes?: string | string[];
  readonly validatorIndices?: string | string[];
  readonly excludeIgnoredAssets?: boolean;
  readonly identifiers?: string[];
  readonly notesSubstring?: string;
  readonly minAmount?: string;
  readonly maxAmount?: string;
  readonly stateMarkers?: string[];
}

export interface HistoryEventExportPayload extends Omit<HistoryEventRequestPayload, 'aggregateByGroupIds' | 'limit' | 'offset'> {
  readonly matchExactEvents: boolean;
}

/** Everything the add-event endpoint accepts, one shape per entry type. */
export type AddHistoryEventPayload = NewHistoryEventPayload | AddSwapEventPayload | AddEvmSwapEventPayload | AddSolanaSwapEventPayload;

/** Everything the edit-event endpoint accepts. */
export type ModifyHistoryEventPayload = EditHistoryEventPayload | EditSwapEventPayload | EditEvmSwapEventPayload | EditSolanaSwapEventPayload;
