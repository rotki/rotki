import type { TablePaginationData } from '@rotki/ui-library';
import type { ComputedRef, Ref, WritableComputedRef } from 'vue';
import type { ConflictResolution } from '@/modules/assets/types';
import type { Collection } from '@/modules/core/common/collection';
import type { ConflictResolutionStrategy } from '@/modules/core/common/common-types';
import type {
  AccountingRuleConflict,
  AccountingRuleConflictRequestPayload,
  AccountingRuleConflictResolution,
} from '@/modules/settings/types/accounting';
import { getCollectionData } from '@/modules/core/common/data/collection-utils';
import { useMessageStore } from '@/modules/core/common/use-message-store';
import { useServerTable } from '@/modules/core/table/use-server-table';
import { useAccountingSettings } from '@/modules/settings/accounting/use-accounting-settings';

interface UseAccountingRuleConflictResolutionOptions {
  /** Called once every conflict has been resolved, so the caller can refresh and close. */
  onResolved: () => void;
}

interface UseAccountingRuleConflictResolutionReturn {
  /** The conflicts on the current page. */
  collection: Ref<Collection<AccountingRuleConflict>>;
  /** The last fetch failure, so the table can name it in place of its empty text. */
  error: Ref<unknown>;
  /** Whether the page is being read. */
  isLoading: Ref<boolean>;
  /** Whether a resolution is being submitted. */
  loading: Readonly<Ref<boolean>>;
  /** The per-conflict choices the user has made so far, keyed by local id. */
  modelResolution: Ref<ConflictResolution>;
  /**
   * One strategy applied to every conflict at once.
   *
   * @remarks
   * It overrides the per-conflict choices entirely, so setting it resolves conflicts the user never
   * looked at. That is why it is a separate deliberate choice rather than a default.
   */
  modelSolveAllUsing: Ref<ConflictResolutionStrategy | undefined>;
  /** Pagination for the conflicts table. */
  pagination: WritableComputedRef<TablePaginationData>;
  /** Re-reads the current page. */
  refetch: () => Promise<void>;
  /** How many conflicts are still unanswered. */
  remaining: ComputedRef<number>;
  /** How many conflicts the user has answered individually. */
  resolutionLength: ComputedRef<number>;
  /** Submits the resolution, reporting a failure as a message and leaving the dialog open. */
  save: () => Promise<void>;
  /** Whether there is anything to submit. */
  valid: ComputedRef<boolean>;
}

/**
 * Drives the accounting rule conflicts dialog: the conflicts table, the per-conflict and
 * resolve-everything choices, and submitting them.
 *
 * @returns the table state, the resolution the user is building, and the submit
 */
export function useAccountingRuleConflictResolution(
  options: UseAccountingRuleConflictResolutionOptions,
): UseAccountingRuleConflictResolutionReturn {
  const { onResolved } = options;

  const { t } = useI18n({ useScope: 'global' });

  const modelResolution = ref<ConflictResolution>({});
  const modelSolveAllUsing = ref<ConflictResolutionStrategy>();
  const loading = shallowRef<boolean>(false);

  const { setMessage } = useMessageStore();
  const { getAccountingRulesConflicts, resolveAccountingRuleConflicts } = useAccountingSettings();

  const { collection, error, isLoading, pagination, refetch } = useServerTable<
    AccountingRuleConflict,
    AccountingRuleConflictRequestPayload
  >({
    fetch: getAccountingRulesConflicts,
    urlState: { mode: 'route' },
  });

  const { total } = getCollectionData<AccountingRuleConflict>(collection);

  const resolutionLength = computed<number>(() => Object.keys(get(modelResolution)).length);

  const remaining = computed<number>(() => get(total) - get(resolutionLength));

  const valid = computed<boolean>(() => !!get(modelSolveAllUsing) || get(resolutionLength) > 0);

  function buildPayload(): AccountingRuleConflictResolution {
    const solveAllVal = get(modelSolveAllUsing);
    if (solveAllVal)
      return { solveAllUsing: solveAllVal };

    const resolutionVal = get(modelResolution);
    const conflicts = Object.keys(resolutionVal).map(localId => ({
      localId,
      solveUsing: resolutionVal[localId],
    }));

    return { conflicts };
  }

  async function save(): Promise<void> {
    set(loading, true);

    const result = await resolveAccountingRuleConflicts(buildPayload());

    if (result.success) {
      onResolved();
    }
    else {
      setMessage({
        description: t('accounting_settings.rule.conflicts.error.description', {
          error: result.message,
        }),
        success: false,
        title: t('accounting_settings.rule.conflicts.error.title'),
      });
    }

    set(loading, false);
  }

  return {
    collection,
    error,
    isLoading,
    loading: readonly(loading),
    modelResolution,
    modelSolveAllUsing,
    pagination,
    refetch,
    remaining,
    resolutionLength,
    save,
    valid,
  };
}
