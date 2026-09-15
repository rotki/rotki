import type { ComputedRef } from 'vue';
import { none, some } from 'plainfp/option';
import { type ActionItem, type ActionItemOption, ActionSeverity, type ActionTarget, applicable, createActionItem } from '@/modules/core/action-center/types';
import { displayDateFormatter } from '@/modules/core/common/date-formatter';
import { useHistorySyncStatus } from '@/modules/history/sync-status/use-history-sync-status';
import { useScramble } from '@/modules/settings/use-scramble';
import { useSetting } from '@/modules/settings/use-setting';

const HISTORY_EVENTS: ActionTarget = { kind: 'route', to: { name: '/history/events/' } };

/** The date format without a timezone part, the way `DateDisplay` renders a date by default. */
function withoutTimezone(format: string): string {
  return format.replace('%z', '').replace('%Z', '').trim();
}

/**
 * The history sync row: history was never downloaded, or not refreshed within the out-of-sync period.
 *
 * @remarks
 * Dismissing it keeps the row listed but stops it counting, until the dismissal threshold passes or
 * a major or minor update resets it. A user with no history sources gets no row at all.
 */
export function useHistorySyncRow(): ComputedRef<ActionItem[]> {
  const { t } = useI18n({ useScope: 'global' });

  const {
    dismiss,
    dismissedRecently,
    hasTxAccounts,
    isNeverQueried,
    justUpdated,
    lastQueriedTimestamp,
    longQuery,
    outOfSync,
    processing,
    recordAppVersion,
  } = useHistorySyncStatus();
  const dateDisplayFormat = useSetting('dateDisplayFormat');
  const { scrambleTimestamp } = useScramble();

  const lastSynced = useTimeAgo(lastQueriedTimestamp);

  const lastSyncedDate = computed<string>(() => displayDateFormatter.format(
    new Date(scrambleTimestamp(get(lastQueriedTimestamp), true)),
    withoutTimezone(get(dateDisplayFormat)),
  ));

  const title = computed<string>(() => {
    if (!get(outOfSync))
      return t('action_center.rows.history.sync.title_synced');
    if (get(justUpdated))
      return t('action_center.rows.history.sync.title_updated');
    if (get(isNeverQueried))
      return t('action_center.rows.history.sync.title_never');
    return t('action_center.rows.history.sync.title', { time: get(lastSynced) });
  });

  const description = computed<string>(() => {
    if (get(justUpdated))
      return t('action_center.rows.history.sync.description_updated');
    if (get(isNeverQueried))
      return t('action_center.rows.history.sync.description_never');
    if (get(longQuery))
      return t('action_center.rows.history.sync.description_long', { date: get(lastSyncedDate) });
    return t('action_center.rows.history.sync.description', { date: get(lastSyncedDate) });
  });

  recordAppVersion();

  return computed<ActionItem[]>(() => {
    if (!get(hasTxAccounts))
      return [];

    const setAside = get(dismissedRecently);

    return [createActionItem<ActionTarget, string>({
      actionLabel: t('action_center.rows.history.sync.action'),
      count: get(outOfSync) ? 1 : 0,
      description: get(description),
      icon: 'lu-history',
      id: 'history-sync',
      informational: setAside,
      loading: get(processing),
      options: applicable<ActionItemOption>([
        setAside ? none : some({ icon: 'lu-x', id: 'dismiss', label: t('action_center.dismiss'), target: { kind: 'run', run: dismiss } }),
      ]),
      severity: ActionSeverity.INFO,
      target: HISTORY_EVENTS,
      title: get(title),
    })];
  });
}
