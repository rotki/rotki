import type { PaginationRequestPayload } from '@/modules/common/common-types';
import type { FilterObjectWithBehaviour } from '@/modules/table/filtering';

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
  readonly stateMarkers?: string[];
}

export interface HistoryEventExportPayload extends Omit<HistoryEventRequestPayload, 'aggregateByGroupIds' | 'limit' | 'offset'> {
  readonly matchExactEvents: boolean;
}
