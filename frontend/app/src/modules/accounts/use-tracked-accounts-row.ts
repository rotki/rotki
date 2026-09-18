import type { ComputedRef } from 'vue';
import { useTrackedEntities } from '@/modules/accounts/use-tracked-entities';
import { type ActionItem, type ActionTarget, ActionUrgency, createActionItem } from '@/modules/core/action-center/types';
import { useAddSourceOptions } from '@/modules/dashboard/holdings/use-add-source-options';

export const TRACKED_ACCOUNTS_ROW_ID = 'no-tracked-accounts';

type TrackedAccountsRow = ActionItem<ActionTarget, typeof TRACKED_ACCOUNTS_ROW_ID>;

interface UseTrackedAccountsRowReturn {
  row: ComputedRef<TrackedAccountsRow>;
  /** Nothing is tracked, and the accounts were read, so that is an answer rather than a gap. */
  raised: ComputedRef<boolean>;
}

/**
 * The "nothing is tracked" row, whose count is a boolean unlike every other row's.
 *
 * @remarks
 * There is one thing to do here, not N of them, and the badge counts categories rather than items,
 * so it slots in as a count of one. The action center lists it, and the empty states that would
 * otherwise explain the same thing in their own words render it instead. Its action offers every
 * kind of source, the same list as the dashboard's "Add a source" menu.
 */
export function useTrackedAccountsRow(): UseTrackedAccountsRowReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { loading, tracksNothing } = useTrackedEntities();
  const addSourceOptions = useAddSourceOptions();

  const row = computed<TrackedAccountsRow>(() => createActionItem<ActionTarget, typeof TRACKED_ACCOUNTS_ROW_ID>({
    actionLabel: t('transactions.alerts.issues.no_tracked_accounts.action'),
    choices: get(addSourceOptions).map(({ icon, key, label, to }) => ({
      icon,
      id: `add-${key}`,
      label,
      target: { kind: 'route', to },
    })),
    count: get(tracksNothing) ? 1 : 0,
    description: t('transactions.alerts.issues.no_tracked_accounts.description'),
    icon: 'lu-wallet',
    id: TRACKED_ACCOUNTS_ROW_ID,
    loading: get(loading),
    target: { kind: 'route', to: { name: '/accounts/' } },
    title: t('transactions.alerts.issues.no_tracked_accounts.title'),
    urgency: ActionUrgency.DECISION,
  }));

  const raised = computed<boolean>(() => !get(loading) && get(tracksNothing));

  return { raised, row };
}
