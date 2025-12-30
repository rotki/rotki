import type { PaginationRequestPayload } from '@/types/common';
import type { FilterObjectWithBehaviour } from '@/types/filtering';

export interface HistoryEventRequestPayload extends PaginationRequestPayload<{ timestamp: number }> {
  readonly fromTimestamp?: string | number;
  readonly toTimestamp?: string | number;
  readonly aggregateByGroupIds: boolean;
  readonly groupIdentifiers?: string | string[];
  readonly eventTypes?: string | string[] | FilterObjectWithBehaviour<string | string[]>;
  readonly eventSubtypes?: string | string[] | FilterObjectWithBehaviour<string | string[]>;
  readonly locationLabels?: string | string[];
  readonly asset?: string;
  readonly counterparties?: string | string[] | FilterObjectWithBehaviour<string | string[]>;
  readonly location?: string | FilterObjectWithBehaviour<string>;
  readonly products?: string | string[];
  readonly entryTypes?: FilterObjectWithBehaviour<string | string[]>;
  readonly txHashes?: string | string[];
  readonly validatorIndices?: string | string[] | FilterObjectWithBehaviour<string | string[]>;
  readonly customizedEventsOnly?: boolean;
  readonly excludeIgnoredAssets?: boolean;
  readonly identifiers?: string[];
  readonly notesSubstring?: string;
}

export interface HistoryEventExportPayload extends Omit<HistoryEventRequestPayload, 'aggregateByGroupIds' | 'limit' | 'offset'> {
  readonly matchExactEvents: boolean;
}
