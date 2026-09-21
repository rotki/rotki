import type { RouteLocationRaw } from 'vue-router';
import { msg } from '@/message-key';

interface UsageKind {
  readonly labelKey: string;
  /** The page listing this kind of data for a location, where the app has one. */
  readonly to?: (identifier: string) => RouteLocationRaw;
}

/**
 * The kinds of reference the backend counts, keyed as the API client hands them over: the wire
 * sends `history_events`, which arrives camel-cased like every other response key.
 */
const USAGE_KINDS = new Map<string, UsageKind>([
  ['bitcoinTransactions', { labelKey: msg.$t('location_manager.usage.kinds.bitcoin_transactions') }],
  ['children', { labelKey: msg.$t('location_manager.usage.kinds.children') }],
  ['dataIssues', { labelKey: msg.$t('location_manager.usage.kinds.data_issues') }],
  ['eventMetrics', { labelKey: msg.$t('location_manager.usage.kinds.event_metrics') }],
  ['historyEvents', {
    labelKey: msg.$t('location_manager.usage.kinds.history_events'),
    to: (location): RouteLocationRaw => ({ name: '/history/events/', query: { location } }),
  }],
  ['historyEventsBackup', { labelKey: msg.$t('location_manager.usage.kinds.history_events_backup') }],
  ['integrationConnections', { labelKey: msg.$t('location_manager.usage.kinds.integration_connections') }],
  ['manuallyTrackedBalances', {
    labelKey: msg.$t('location_manager.usage.kinds.manually_tracked_balances'),
    to: (): RouteLocationRaw => ({ name: '/balances/manual/[[tab]]' }),
  }],
  ['marginPositions', { labelKey: msg.$t('location_manager.usage.kinds.margin_positions') }],
  ['skippedExternalEvents', { labelKey: msg.$t('location_manager.usage.kinds.skipped_external_events') }],
  ['timedLocationData', {
    labelKey: msg.$t('location_manager.usage.kinds.timed_location_data'),
    to: (): RouteLocationRaw => ({ name: '/statistics/snapshots/' }),
  }],
]);

export interface LocationUsageEntry {
  /** The i18n key naming the kind, or undefined for a kind this version does not know. */
  readonly labelKey: string | undefined;
  readonly kind: string;
  readonly count: number;
  /** Where the user can see this data, to move or remove it. */
  readonly to: RouteLocationRaw | undefined;
}

export function locationUsageEntries(usage: Record<string, number>, identifier: string): LocationUsageEntry[] {
  return Object.entries(usage)
    .map(([kind, count]) => {
      const known = USAGE_KINDS.get(kind);
      return { count, kind, labelKey: known?.labelKey, to: known?.to?.(identifier) };
    })
    .sort((a, b) => b.count - a.count);
}
