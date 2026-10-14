<script setup lang="ts">
import type { DataTableColumn, TablePaginationData } from '@rotki/ui-library';
import type { Collection } from '@/modules/core/common/collection';
import type { AccountingRuleEntry } from '@/modules/settings/types/accounting';
import { useTableEmptyState } from '@/modules/core/table/use-table-empty-state';
import AccountingRuleColumnHeader from '@/modules/settings/accounting/rule/AccountingRuleColumnHeader.vue';
import AccountingRuleEventCell from '@/modules/settings/accounting/rule/AccountingRuleEventCell.vue';
import AccountingRuleEventsDialog from '@/modules/settings/accounting/rule/AccountingRuleEventsDialog.vue';
import AccountingRuleWithLinkedSettingDisplay from '@/modules/settings/accounting/rule/AccountingRuleWithLinkedSettingDisplay.vue';
import AccountingTreatmentChip from '@/modules/settings/accounting/rule/AccountingTreatmentChip.vue';
import CounterpartyDisplay from '@/modules/shell/components/display/CounterpartyDisplay.vue';
import RowActions from '@/modules/shell/components/RowActions.vue';

interface AccountingRuleTableProps {
  state: Collection<AccountingRuleEntry>;
  pagination: TablePaginationData;
  isLoading: boolean;
  isCustom: boolean;
}

const paginationModel = defineModel<TablePaginationData>('pagination', { required: true });

const { isCustom } = defineProps<AccountingRuleTableProps>();

const emit = defineEmits<{
  'delete-click': [item: AccountingRuleEntry];
  'edit-click': [item: AccountingRuleEntry];
  'view-events-click': [item: AccountingRuleEntry];
}>();

const { t } = useI18n({ useScope: 'global' });

const emptyState = useTableEmptyState();

const selectedEventIds = ref<number[]>([]);
const eventsDialogOpen = ref<boolean>(false);

/**
 * The table's columns, with an extra one in the custom-rule view.
 *
 * @remarks
 * A custom rule gains an event-ids column and keeps the others, so that view is the regular set plus
 * one rather than a different set.
 */
const cols = computed<DataTableColumn<AccountingRuleEntry>[]>(() => {
  const columns: DataTableColumn<AccountingRuleEntry>[] = [
    {
      cellClass: 'max-w-56',
      key: 'event',
      label: t('accounting_settings.rule.labels.event'),
    },
    {
      key: 'counterparty',
      label: t('common.counterparty'),
    },
  ];

  if (isCustom) {
    columns.push({
      key: 'eventIds',
      label: t('accounting_settings.rule.labels.event_ids'),
    });
  }

  columns.push(
    {
      align: 'center',
      key: 'taxable',
      label: t('accounting_settings.rule.labels.taxable'),
    },
    {
      align: 'center',
      key: 'countEntireAmountSpend',
      label: t('accounting_settings.rule.labels.count_entire_amount_spend'),
    },
    {
      align: 'center',
      key: 'countCostBasisPnl',
      label: t('accounting_settings.rule.labels.count_cost_basis_pnl'),
    },
    {
      key: 'accountingTreatment',
      label: t('accounting_settings.rule.labels.accounting_treatment'),
    },
    {
      align: 'end',
      class: 'w-px',
      key: 'actions',
      label: '',
    },
  );

  return columns;
});

function openEventsDialog(eventIds: number[]): void {
  set(selectedEventIds, eventIds);
  set(eventsDialogOpen, true);
}
</script>

<template>
  <RuiDataTable
    v-model:pagination.external="paginationModel"
    dense
    disable-sticky-pagination
    :rows="state.data"
    :cols="cols"
    :empty="emptyState"
    :loading="isLoading"
    row-attr="identifier"
    data-testid="accounting-rule-table"
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
        :event-type="row.eventType"
        :event-subtype="row.eventSubtype"
      />
    </template>
    <template #item.counterparty="{ row }">
      <CounterpartyDisplay
        v-if="row.counterparty"
        class="whitespace-nowrap"
        :counterparty="row.counterparty"
      />
      <span
        v-else
        class="text-rui-text-secondary"
      >
        -
      </span>
    </template>
    <template #item.taxable="{ row }">
      <AccountingRuleWithLinkedSettingDisplay
        identifier="taxable"
        :item="row.taxable"
      />
    </template>
    <template #item.countEntireAmountSpend="{ row }">
      <AccountingRuleWithLinkedSettingDisplay
        identifier="countEntireAmountSpend"
        :item="row.countEntireAmountSpend"
      />
    </template>
    <template #item.countCostBasisPnl="{ row }">
      <AccountingRuleWithLinkedSettingDisplay
        identifier="countCostBasisPnl"
        :item="row.countCostBasisPnl"
      />
    </template>
    <template #item.accountingTreatment="{ row }">
      <AccountingTreatmentChip :treatment="row.accountingTreatment" />
    </template>
    <template #item.eventIds="{ row }">
      <div class="flex items-center gap-1 text-sm">
        <span>{{ row.eventIds?.length || 0 }} {{ t('common.events') }}</span>
        <RuiButton
          v-if="row.eventIds && row.eventIds.length > 0"
          variant="text"
          icon
          size="sm"
          @click="openEventsDialog(row.eventIds)"
        >
          <RuiIcon
            name="lu-arrow-right"
            size="16"
          />
        </RuiButton>
      </div>
    </template>
    <template #item.actions="{ row }">
      <RowActions
        align="end"
        class="text-rui-text-secondary transition-opacity [tr:not(:hover)_&:not(:focus-within)]:opacity-0 motion-reduce:transition-none"
        :delete-tooltip="t('accounting_settings.rule.delete')"
        :edit-tooltip="t('accounting_settings.rule.edit')"
        @delete-click="emit('delete-click', row)"
        @edit-click="emit('edit-click', row)"
      >
        <RuiButton
          v-if="!isCustom && row.eventType"
          variant="text"
          icon
          :title="t('accounting_settings.rule.view_events')"
          data-testid="view-events"
          @click="emit('view-events-click', row)"
        >
          <RuiIcon
            size="16"
            name="lu-list-filter"
          />
        </RuiButton>
      </RowActions>
    </template>
  </RuiDataTable>

  <AccountingRuleEventsDialog
    v-if="eventsDialogOpen"
    :event-ids="selectedEventIds"
    @close="eventsDialogOpen = false"
  />
</template>
