<script lang="ts" setup>
import type { DataTableColumn } from '@rotki/ui-library';
import type { ConflictResolutionStrategy } from '@/modules/core/common/common-types';
import type { AccountingRuleConflict } from '@/modules/settings/types/accounting';
import { getCollectionData } from '@/modules/core/common/data/collection-utils';
import ScrollableDialogContent from '@/modules/core/table/ScrollableDialogContent.vue';
import { useTableEmptyState } from '@/modules/core/table/use-table-empty-state';
import { CONFLICT_PROPERTIES, type ConflictProperty, propertyDiffers } from '@/modules/settings/accounting/rule/accounting-rule-conflicts';
import AccountingRuleColumnHeader from '@/modules/settings/accounting/rule/AccountingRuleColumnHeader.vue';
import AccountingRuleConflictCell from '@/modules/settings/accounting/rule/AccountingRuleConflictCell.vue';
import AccountingRuleEventCell from '@/modules/settings/accounting/rule/AccountingRuleEventCell.vue';
import AccountingRuleWithLinkedSettingDisplay
  from '@/modules/settings/accounting/rule/AccountingRuleWithLinkedSettingDisplay.vue';
import AccountingTreatmentChip from '@/modules/settings/accounting/rule/AccountingTreatmentChip.vue';
import { useAccountingRuleConflictResolution } from '@/modules/settings/accounting/rule/use-accounting-rule-conflict-resolution';
import BigDialog from '@/modules/shell/components/dialogs/BigDialog.vue';
import CounterpartyDisplay from '@/modules/shell/components/display/CounterpartyDisplay.vue';

type Strategy = ConflictResolutionStrategy | 'per_rule';

const emit = defineEmits<{
  close: [];
  refresh: [];
}>();

const close = (): void => emit('close');

const { t } = useI18n({ useScope: 'global' });

const {
  collection,
  error,
  isLoading,
  loading,
  modelResolution,
  modelSolveAllUsing,
  pagination,
  refetch,
  remaining,
  resolutionLength,
  save,
  valid,
} = useAccountingRuleConflictResolution({
  onResolved: (): void => {
    emit('refresh');
    close();
  },
});

const emptyState = useTableEmptyState({ error });

const { total } = getCollectionData<AccountingRuleConflict>(collection);

/** The bulk choice as one control: choosing per rule is the absence of a bulk strategy. */
const strategy = computed<Strategy>({
  get: () => get(modelSolveAllUsing) ?? 'per_rule',
  set: (value: Strategy) => set(modelSolveAllUsing, value === 'per_rule' ? undefined : value),
});

/** The pagination bar only earns its place once the conflicts run past one page. */
const singlePage = computed<boolean>(() => get(total) <= get(pagination).limit);

const PROPERTY_LABELS = computed<Record<ConflictProperty, string>>(() => ({
  accountingTreatment: t('accounting_settings.rule.labels.accounting_treatment'),
  countCostBasisPnl: t('accounting_settings.rule.labels.count_cost_basis_pnl'),
  countEntireAmountSpend: t('accounting_settings.rule.labels.count_entire_amount_spend'),
  taxable: t('accounting_settings.rule.labels.taxable'),
}));

/**
 * The properties some conflict on this page disagrees on. A property every version agrees on cannot
 * be what the choice is about, so its column is left out and named in a note under the table. With
 * nothing loaded yet, every column shows.
 */
const differingProperties = computed<ConflictProperty[]>(() => {
  const rows = get(collection).data;
  if (rows.length === 0)
    return [...CONFLICT_PROPERTIES];
  return CONFLICT_PROPERTIES.filter(property => rows.some(row => propertyDiffers(row, property)));
});

const matchingLabels = computed<string[]>(() => {
  const differing = get(differingProperties);
  return CONFLICT_PROPERTIES.filter(property => !differing.includes(property)).map(property => get(PROPERTY_LABELS)[property]);
});

const tableHeaders = computed<DataTableColumn<AccountingRuleConflict>[]>(() => {
  const columns: DataTableColumn<AccountingRuleConflict>[] = [
    {
      key: 'event',
      label: t('accounting_settings.rule.labels.event'),
    },
    {
      key: 'counterparty',
      label: t('common.counterparty'),
    },
  ];

  for (const property of get(differingProperties)) {
    columns.push({
      align: 'center',
      cellClass: 'p-0!',
      key: property,
      label: get(PROPERTY_LABELS)[property],
    });
  }

  // A bulk choice decides every row, so the per-row buttons would only be disabled noise.
  if (!get(modelSolveAllUsing)) {
    columns.push({
      align: 'center',
      class: 'w-px',
      key: 'actions',
      label: t('accounting_settings.rule.conflicts.labels.choose_version'),
    });
  }

  return columns;
});

/** What Save will do: settle every conflict at once, or write the choices made so far and leave the rest. */
const saveLabel = computed<string>(() => {
  if (get(modelSolveAllUsing))
    return t('accounting_settings.rule.conflicts.save.all', { total: get(total) });
  const count = get(resolutionLength);
  return t('accounting_settings.rule.conflicts.save.choices', { count }, count);
});

/** The version that will win for a row, whether picked for it alone or for every row at once. */
function chosenFor(row: AccountingRuleConflict): ConflictResolutionStrategy | undefined {
  return get(modelSolveAllUsing) ?? get(modelResolution)[row.localId];
}

onMounted(async () => {
  await refetch();
});
</script>

<template>
  <BigDialog
    :action="{ disabled: !valid, primary: saveLabel }"
    display
    :layout="{ maxWidth: '64rem', fill: true, autoHeight: true }"
    :loading="loading"
    :persistent="resolutionLength > 0"
    :title="t('accounting_settings.rule.conflicts.title')"
    :subtitle="t('accounting_settings.rule.conflicts.subtitle')"
    @cancel="close()"
    @confirm="save()"
  >
    <ScrollableDialogContent fill>
      <template #header>
        <div class="flex flex-wrap items-center justify-between gap-3 pb-4">
          <span
            class="text-sm text-rui-text-secondary"
            data-testid="accounting-rule-conflicts-summary"
          >
            <template v-if="strategy === 'local'">
              {{ t('accounting_settings.rule.conflicts.summary.all_local') }}
            </template>
            <template v-else-if="strategy === 'remote'">
              {{ t('accounting_settings.rule.conflicts.summary.all_remote') }}
            </template>
            <template v-else>
              {{ t('accounting_settings.rule.conflicts.summary.remaining', { remaining, total }) }}
            </template>
          </span>
          <RuiButtonGroup
            v-model="strategy"
            color="primary"
            variant="outlined"
            size="sm"
            required
            data-testid="accounting-rule-conflicts-strategy"
          >
            <RuiButton model-value="per_rule">
              {{ t('accounting_settings.rule.conflicts.strategy.per_rule') }}
            </RuiButton>
            <RuiButton model-value="local">
              {{ t('accounting_settings.rule.conflicts.strategy.keep_local') }}
            </RuiButton>
            <RuiButton model-value="remote">
              {{ t('accounting_settings.rule.conflicts.strategy.keep_remote') }}
            </RuiButton>
          </RuiButtonGroup>
        </div>
      </template>

      <RuiDataTable
        v-model:pagination.external="pagination"
        :cols="tableHeaders"
        :empty="emptyState"
        :loading="isLoading"
        :rows="collection.data"
        :hide-pagination="singlePage"
        disable-floating-header
        :mobile-breakpoint="0"
        outlined
        row-attr="localId"
      >
        <template #header.taxable>
          <AccountingRuleColumnHeader
            :label="t('accounting_settings.rule.labels.taxable')"
            :hint="t('accounting_settings.rule.labels.taxable_subtitle')"
          />
        </template>
        <template #header.countEntireAmountSpend>
          <AccountingRuleColumnHeader
            :label="t('accounting_settings.rule.labels.count_entire_amount_spend')"
            :hint="t('accounting_settings.rule.labels.count_entire_amount_spend_subtitle')"
          />
        </template>
        <template #header.countCostBasisPnl>
          <AccountingRuleColumnHeader
            :label="t('accounting_settings.rule.labels.count_cost_basis_pnl')"
            :hint="t('accounting_settings.rule.labels.count_cost_basis_pnl_subtitle')"
          />
        </template>
        <template #header.accountingTreatment>
          <AccountingRuleColumnHeader :label="t('accounting_settings.rule.labels.accounting_treatment')" />
        </template>
        <template #item.event="{ row }">
          <AccountingRuleEventCell
            :event-type="row.localData.eventType"
            :event-subtype="row.localData.eventSubtype"
          />
        </template>
        <template #item.counterparty="{ row }">
          <CounterpartyDisplay
            v-if="row.localData.counterparty"
            :counterparty="row.localData.counterparty"
          />
          <span
            v-else
            class="text-rui-text-secondary"
          >
            -
          </span>
        </template>
        <template #item.taxable="{ row }">
          <AccountingRuleConflictCell
            :differs="propertyDiffers(row, 'taxable')"
            :chosen="chosenFor(row)"
          >
            <template #local>
              <AccountingRuleWithLinkedSettingDisplay
                :item="row.localData.taxable"
                identifier="taxable"
              />
            </template>
            <template #remote>
              <AccountingRuleWithLinkedSettingDisplay
                :item="row.remoteData.taxable"
                identifier="taxable"
              />
            </template>
          </AccountingRuleConflictCell>
        </template>
        <template #item.countEntireAmountSpend="{ row }">
          <AccountingRuleConflictCell
            :differs="propertyDiffers(row, 'countEntireAmountSpend')"
            :chosen="chosenFor(row)"
          >
            <template #local>
              <AccountingRuleWithLinkedSettingDisplay
                :item="row.localData.countEntireAmountSpend"
                identifier="countEntireAmountSpend"
              />
            </template>
            <template #remote>
              <AccountingRuleWithLinkedSettingDisplay
                :item="row.remoteData.countEntireAmountSpend"
                identifier="countEntireAmountSpend"
              />
            </template>
          </AccountingRuleConflictCell>
        </template>
        <template #item.countCostBasisPnl="{ row }">
          <AccountingRuleConflictCell
            :differs="propertyDiffers(row, 'countCostBasisPnl')"
            :chosen="chosenFor(row)"
          >
            <template #local>
              <AccountingRuleWithLinkedSettingDisplay
                :item="row.localData.countCostBasisPnl"
                identifier="countCostBasisPnl"
              />
            </template>
            <template #remote>
              <AccountingRuleWithLinkedSettingDisplay
                :item="row.remoteData.countCostBasisPnl"
                identifier="countCostBasisPnl"
              />
            </template>
          </AccountingRuleConflictCell>
        </template>
        <template #item.accountingTreatment="{ row }">
          <AccountingRuleConflictCell
            :differs="propertyDiffers(row, 'accountingTreatment')"
            :chosen="chosenFor(row)"
          >
            <template #local>
              <AccountingTreatmentChip :treatment="row.localData.accountingTreatment" />
            </template>
            <template #remote>
              <AccountingTreatmentChip :treatment="row.remoteData.accountingTreatment" />
            </template>
          </AccountingRuleConflictCell>
        </template>
        <template #item.actions="{ row }">
          <RuiButtonGroup
            v-model="modelResolution[row.localId]"
            color="primary"
            required
            variant="outlined"
            vertical
            size="sm"
          >
            <RuiButton
              class="h-10 w-20"
              model-value="local"
            >
              {{ t('conflict_dialog.action.local') }}
            </RuiButton>
            <RuiButton
              class="h-10 w-20"
              model-value="remote"
            >
              {{ t('conflict_dialog.action.remote') }}
            </RuiButton>
          </RuiButtonGroup>
        </template>
      </RuiDataTable>
      <p
        v-if="matchingLabels.length > 0"
        class="pt-3 text-xs text-rui-text-secondary"
        data-testid="accounting-rule-conflicts-matching"
      >
        {{ t('accounting_settings.rule.conflicts.matching', { properties: matchingLabels.join(', ') }) }}
      </p>
    </ScrollableDialogContent>
  </BigDialog>
</template>
