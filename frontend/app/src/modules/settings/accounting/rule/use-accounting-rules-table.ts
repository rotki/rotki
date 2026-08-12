import type { TablePaginationData } from '@rotki/ui-library';
import type { ComputedRef, Ref, WritableComputedRef } from 'vue';
import type { Collection } from '@/modules/core/common/collection';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import type { Filters } from '@/modules/settings/accounting/rule/use-accounting-rule-filter';
import type { AccountingRuleEntry, AccountingRuleRequestPayload } from '@/modules/settings/types/accounting';
import { useServerTable } from '@/modules/core/table/use-server-table';
import { CustomRuleHandling } from '@/modules/settings/accounting/rule/accounting-rule-query';
import { useAccountingRuleFields } from '@/modules/settings/accounting/rule/use-accounting-rule-fields';
import { useAccountingSettings } from '@/modules/settings/accounting/use-accounting-settings';

interface UseAccountingRulesTableReturn {
  collection: Ref<Collection<AccountingRuleEntry>>;
  /** The pill-bar fields, built here because the table's url shape is read off them. */
  fields: ComputedRef<FieldDef[]>;
  filter: WritableComputedRef<Filters>;
  isLoading: Ref<boolean>;
  /** Which half of the rules is shown; a tab, and a request/url param. */
  modelCustomRuleHandling: Ref<CustomRuleHandling>;
  pagination: WritableComputedRef<TablePaginationData>;
  refetch: () => Promise<void>;
  showsCustomRules: ComputedRef<boolean>;
}

/**
 * The accounting rules table: its server-side collection, its filter, and the regular/custom split
 * the tabs drive. The split is a param source rather than a filter so it rides both the request and
 * the url, which is what keeps a link to the custom tab pointing at the custom tab.
 */
export function useAccountingRulesTable(): UseAccountingRulesTableReturn {
  const { getAccountingRules } = useAccountingSettings();

  const modelCustomRuleHandling = shallowRef<CustomRuleHandling>(CustomRuleHandling.EXCLUDE);
  // Owned here rather than left to the table: the subtype field narrows by the picked event types,
  // so the fields read the bag, and they are built before the table that would otherwise own it.
  const modelFilters = ref<Filters>({});
  const fields = useAccountingRuleFields(modelFilters);

  const {
    collection,
    filter,
    isLoading,
    pagination,
    refetch,
  } = useServerTable<AccountingRuleEntry, AccountingRuleRequestPayload, Filters>({
    fetch: getAccountingRules,
    fields,
    filters: modelFilters,
    params: [{
      to: 'both',
      values: computed<Record<string, unknown>>(() => ({
        customRuleHandling: get(modelCustomRuleHandling),
      })),
    }],
    urlState: { mode: 'route' },
  });

  return {
    collection,
    fields,
    filter,
    isLoading,
    modelCustomRuleHandling,
    pagination,
    refetch,
    showsCustomRules: computed<boolean>(() => get(modelCustomRuleHandling) === CustomRuleHandling.ONLY),
  };
}
