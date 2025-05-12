import type { PaginationRequestPayload } from '@/types/common';
import type { FilterObjectWithBehaviour } from '@/types/filtering';

export interface HistoryEventRequestPayload extends PaginationRequestPayload<{ timestamp: number }> {
  readonly fromTimestamp?: string | number;
  readonly toTimestamp?: string | number;
  readonly groupByEventIds: boolean;
  readonly eventIdentifiers?: string | string[];
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
  readonly customizedEventsOnly?: boolean;
  readonly excludeIgnoredAssets?: boolean;
  readonly identifiers?: string[];
}

export interface HistoryEventExportPayload extends HistoryEventRequestPayload {
  readonly matchExactEvents: boolean;
}
