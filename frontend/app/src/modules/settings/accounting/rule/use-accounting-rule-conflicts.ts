import type { Ref } from 'vue';
import { match } from 'plainfp/result';
import { useAccountingRuleConflictsCount } from '@/modules/settings/accounting/rule/use-accounting-rule-conflicts-count';

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
 * The action center links here with `?resolveConflicts`, so the count is also what decides whether
 * that link opens the dialog: asking for conflicts when there are none should land on the page, not
 * on an empty dialog. Unknown counts open it too, so its table can say why they could not load. The
 * parameter is consumed either way, so a reload does not reopen it.
 */
export function useAccountingRuleConflicts(): UseAccountingRuleConflictsReturn {
  const router = useRouter();
  const route = useRoute();
  const { count, refresh } = useAccountingRuleConflictsCount();

  const modelConflictsDialogOpen = shallowRef<boolean>(false);

  async function checkConflicts(): Promise<void> {
    const recount = await refresh();

    if (!get(route).query.resolveConflicts)
      return;

    if (match(recount, { err: () => true, ok: total => total > 0 }))
      set(modelConflictsDialogOpen, true);

    await router.replace({ query: {} });
  }

  return {
    checkConflicts,
    conflictsNumber: count,
    modelConflictsDialogOpen,
  };
}
