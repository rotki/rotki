import { msg } from '@/message-key';

/** What each kind of reference the backend counts is called in the usage dialog. */
const USAGE_LABELS = new Map<string, string>([
  ['bitcoin_transactions', msg.$t('location_manager.usage.kinds.bitcoin_transactions')],
  ['children', msg.$t('location_manager.usage.kinds.children')],
  ['data_issues', msg.$t('location_manager.usage.kinds.data_issues')],
  ['event_metrics', msg.$t('location_manager.usage.kinds.event_metrics')],
  ['history_events', msg.$t('location_manager.usage.kinds.history_events')],
  ['history_events_backup', msg.$t('location_manager.usage.kinds.history_events_backup')],
  ['integration_connections', msg.$t('location_manager.usage.kinds.integration_connections')],
  ['manually_tracked_balances', msg.$t('location_manager.usage.kinds.manually_tracked_balances')],
  ['margin_positions', msg.$t('location_manager.usage.kinds.margin_positions')],
  ['skipped_external_events', msg.$t('location_manager.usage.kinds.skipped_external_events')],
  ['timed_location_data', msg.$t('location_manager.usage.kinds.timed_location_data')],
]);

export interface LocationUsageEntry {
  /** The i18n key naming the kind, or undefined for a kind this version does not know. */
  readonly labelKey: string | undefined;
  readonly kind: string;
  readonly count: number;
}

export function locationUsageEntries(usage: Record<string, number>): LocationUsageEntry[] {
  return Object.entries(usage)
    .map(([kind, count]) => ({ count, kind, labelKey: USAGE_LABELS.get(kind) }))
    .sort((a, b) => b.count - a.count);
}
