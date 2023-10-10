<script setup lang="ts">
import { type DataTableHeader } from 'vuetify';
import { pick } from 'lodash-es';
import { type Collection } from '@/types/collection';
import {
  type Filters,
  type Matcher
} from '@/composables/filters/accounting-rule';
import {
  type AccountingRuleEntry,
  type AccountingRuleRequestPayload
} from '@/types/settings/accounting';
import BooleanDisplay from '@/components/display/BooleanDisplay.vue';
import { useAccountingRuleForm } from '@/composables/settings/accounting/form';

const { t } = useI18n();

const { getAccountingRules } = useAccountingSettings();

const {
  state,
  isLoading,
  options,
  fetchData,
  setOptions,
  setPage,
  filters,
  matchers,
  updateFilter,
  editableItem
} = usePaginationFilters<
  AccountingRuleEntry,
  AccountingRuleRequestPayload,
  AccountingRuleEntry,
  Collection<AccountingRuleEntry>,
  Filters,
  Matcher
>(null, true, useAccountingRuleFilter, getAccountingRules);

onMounted(async () => {
  await fetchData();
});

const tableHeaders = computed<DataTableHeader[]>(() => [
  {
    text: t('accounting_settings.rule.labels.event_type'),
    value: 'eventType',
    sortable: false
  },
  {
    text: t('accounting_settings.rule.labels.event_subtype'),
    value: 'eventSubtype',
    sortable: false
  },
  {
    text: t('accounting_settings.rule.labels.counterparty'),
    value: 'counterparty',
    sortable: false
  },
  {
    text: t('accounting_settings.rule.labels.taxable'),
    value: 'taxable',
    sortable: false,
    width: '100px',
    align: 'center'
  },
  {
    text: t('accounting_settings.rule.labels.count_entire_amount_spend'),
    value: 'countEntireAmountSpend',
    sortable: false,
    width: '150px',
    align: 'center'
  },
  {
    text: t('accounting_settings.rule.labels.count_cost_basis_pnl'),
    value: 'countCostBasisPnl',
    sortable: false,
    width: '100px',
    align: 'center'
  },
  {
    text: t('accounting_settings.rule.labels.method'),
    value: 'method',
    sortable: false
  },
  {
    text: t('accounting_settings.rule.labels.accounting_treatment'),
    value: 'accountingTreatment',
    sortable: false
  },
  {
    text: t('common.actions_text'),
    value: 'actions',
    align: 'center',
    sortable: false,
    width: '1px'
  }
]);

const { historyEventTypesData, historyEventSubTypesData } =
  useHistoryEventMappings();

const getHistoryEventTypeName = (eventType: string): ComputedRef<string> =>
  computed(
    () =>
      get(historyEventTypesData).find(item => item.identifier === eventType)
        ?.label ?? toSentenceCase(eventType)
  );

const getHistoryEventSubTypeName = (
  eventSubtype: string
): ComputedRef<string> =>
  computed(
    () =>
      get(historyEventSubTypesData).find(
        item => item.identifier === eventSubtype
      )?.label ?? toSentenceCase(eventSubtype)
  );

const { setOpenDialog, setPostSubmitFunc } = useAccountingRuleForm();

const add = () => {
  set(editableItem, null);
  setOpenDialog(true);
};

const edit = (rule: AccountingRuleEntry) => {
  set(editableItem, rule);
  setOpenDialog(true);
};

setPostSubmitFunc(fetchData);

const { show } = useConfirmStore();
const { setMessage } = useMessageStore();

const { deleteAccountingRule: deleteAccountingRuleCaller } = useAccountingApi();

const deleteAccountingRule = async (item: AccountingRuleEntry) => {
  try {
    const success = await deleteAccountingRuleCaller(
      pick(item, ['eventType', 'eventSubtype', 'counterparty'])
    );
    if (success) {
      await fetchData();
    }
  } catch {
    setMessage({
      description: t('accounting_settings.rule.delete_error')
    });
  }
};

const showDeleteConfirmation = (item: AccountingRuleEntry) => {
  show(
    {
      title: t('accounting_settings.rule.delete'),
      message: t('accounting_settings.rule.confirm_delete')
    },
    async () => await deleteAccountingRule(item)
  );
};
</script>

<template>
  <div>
    <RuiCard>
      <template #custom-header>
        <div
          class="flex flex-row flex-wrap items-center justify-between gap-4 p-4"
        >
          <div class="flex items-center flex-wrap gap-3">
            <RefreshButton
              :loading="isLoading"
              :tooltip="t('accounting_settings.rule.refresh_tooltip')"
              @refresh="fetchData()"
            />
            <span class="text-h6">
              {{ t('accounting_settings.rule.title') }}
            </span>
          </div>

          <div class="flex items-center flex-wrap gap-2">
            <RuiButton color="primary" @click="add()">
              <template #prepend>
                <RuiIcon name="add-line" />
              </template>
              {{ t('accounting_settings.rule.add') }}
            </RuiButton>
            <div class="w-full md:w-[25rem]">
              <TableFilter
                :matches="filters"
                :matchers="matchers"
                @update:matches="updateFilter($event)"
              />
            </div>
          </div>
        </div>
      </template>
      <CollectionHandler :collection="state" @set-page="setPage($event)">
        <template #default="{ data, itemLength }">
          <DataTable
            :items="data"
            :headers="tableHeaders"
            :loading="isLoading"
            :options="options"
            :server-items-length="itemLength"
            @update:options="setOptions($event)"
          >
            <template #item.eventType="{ item }">
              {{ getHistoryEventTypeName(item.eventType).value }}
            </template>
            <template #item.eventSubtype="{ item }">
              {{ getHistoryEventSubTypeName(item.eventSubtype).value }}
            </template>
            <template #item.counterparty="{ item }">
              <HistoryEventTypeCounterparty
                text
                :event="{ counterparty: item.counterparty }"
              />
            </template>
            <template #item.taxable="{ item }">
              <div class="flex justify-center items-center">
                <BooleanDisplay :display="item.taxable" />
              </div>
            </template>
            <template #item.countEntireAmountSpend="{ item }">
              <div class="flex justify-center items-center">
                <BooleanDisplay :display="item.countEntireAmountSpend" />
              </div>
            </template>
            <template #item.countCostBasisPnl="{ item }">
              <div class="flex justify-center items-center">
                <BooleanDisplay :display="item.countCostBasisPnl" />
              </div>
            </template>
            <template #item.method="{ item }">
              <BadgeDisplay>{{ item.method }}</BadgeDisplay>
            </template>
            <template #item.accountingTreatment="{ item }">
              <BadgeDisplay>{{ item.accountingTreatment }}</BadgeDisplay>
            </template>
            <template #item.actions="{ item }">
              <RowActions
                :delete-tooltip="t('accounting_settings.rule.delete')"
                :edit-tooltip="t('accounting_settings.rule.edit')"
                @delete-click="showDeleteConfirmation(item)"
                @edit-click="edit(item)"
              />
            </template>
          </DataTable>
        </template>
      </CollectionHandler>
    </RuiCard>
    <AccountingRuleFormDialog
      :loading="isLoading"
      :editable-item="editableItem"
    />
  </div>
</template>
