import type { Ref } from 'vue';
import { useAccountingSettings } from '@/modules/settings/accounting/use-accounting-settings';

interface UseAccountingRuleConflictsReturn {
  /** How many rules conflict, which is what the warning button counts. */
  conflictsNumber: Readonly<Ref<number>>;
  modelConflictsDialogOpen: Ref<boolean>;
  /** Re-counts the conflicts, and opens the dialog when the route asked for it. */
  checkConflicts: () => Promise<void>;
}

/**
 * The conflicting-rules count and its dialog.
 *
 * A notification links here with `?resolveConflicts`, so the count is also what decides whether that
 * link opens the dialog: asking for conflicts when there are none should land on the page, not on an
 * empty dialog. The parameter is consumed either way, so a reload does not reopen it.
 */
export function useAccountingRuleConflicts(): UseAccountingRuleConflictsReturn {
  const router = useRouter();
  const route = useRoute();
  const { getAccountingRulesConflicts } = useAccountingSettings();

  const conflictsNumber = shallowRef<number>(0);
  const modelConflictsDialogOpen = shallowRef<boolean>(false);

  async function checkConflicts(): Promise<void> {
    const result = await getAccountingRulesConflicts({ limit: 1, offset: 0 });
    // A failed count keeps the last known one rather than claiming there are no conflicts.
    if (result.ok)
      set(conflictsNumber, result.value.total);

    if (!get(route).query.resolveConflicts)
      return;

    // Unknown counts open too: the dialog's table says why it could not load them.
    if (!result.ok || result.value.total > 0)
      set(modelConflictsDialogOpen, true);

    await router.replace({ query: {} });
  }

  return {
    checkConflicts,
    conflictsNumber: readonly(conflictsNumber),
    modelConflictsDialogOpen,
  };
}
