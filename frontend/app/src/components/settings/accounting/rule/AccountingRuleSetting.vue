<script setup lang="ts">
import { type DataTableHeader } from 'vuetify';
import { type Collection } from '@/types/collection';
import {
  type Filters,
  type Matcher
} from '@/composables/filters/accounting-rule';
import {
  type AccountingRuleEntry,
  type AccountingRuleRequestPayload
} from '@/types/settings/accounting';

const { t } = useI18n();
const router = useRouter();

const { getAccountingRule, getAccountingRules, getAccountingRulesConflicts } =
  useAccountingSettings();

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

const conflictsNumber: Ref<number> = ref(0);

const checkConflicts = async () => {
  const { total } = await getAccountingRulesConflicts({ limit: 1, offset: 0 });
  set(conflictsNumber, total);

  const {
    currentRoute: {
      query: { resolveConflicts }
    }
  } = router;

  if (resolveConflicts) {
    if (total > 0) {
      set(conflictsDialogOpen, true);
    }
    await router.replace({ query: {} });
  }
};

const tableHeaders = computed<DataTableHeader[]>(() => [
  {
    text: `${t('accounting_settings.rule.labels.event_type')} - \n${t(
      'accounting_settings.rule.labels.event_subtype'
    )}`,
    value: 'eventTypeAndSubtype',
    class: 'whitespace-break-spaces',
    cellClass: 'py-4',
    sortable: false
  },
  {
    text: t('transactions.events.form.resulting_combination.label'),
    value: 'resultingCombination',
    sortable: false
  },
  {
    text: t('accounting_settings.rule.labels.counterparty'),
    value: 'counterparty',
    class: 'border-r border-default',
    cellClass: 'border-r border-default',
    sortable: false
  },
  {
    text: t('accounting_settings.rule.labels.taxable'),
    value: 'taxable',
    sortable: false,
    cellClass: 'px-2',
    class: 'px-2',
    align: 'center'
  },
  {
    text: t('accounting_settings.rule.labels.count_entire_amount_spend'),
    value: 'countEntireAmountSpend',
    sortable: false,
    width: '120px',
    cellClass: 'px-2',
    class: 'px-2',
    align: 'center'
  },
  {
    text: t('accounting_settings.rule.labels.count_cost_basis_pnl'),
    value: 'countCostBasisPnl',
    sortable: false,
    width: '120px',
    cellClass: 'px-2',
    class: 'px-2',
    align: 'center'
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

const { historyEventTypesData, historyEventSubTypesData, getEventTypeData } =
  useHistoryEventMappings();

const getHistoryEventTypeName = (eventType: string): string =>
  get(historyEventTypesData).find(item => item.identifier === eventType)
    ?.label ?? toSentenceCase(eventType);

const getHistoryEventSubTypeName = (eventSubtype: string): string =>
  get(historyEventSubTypesData).find(item => item.identifier === eventSubtype)
    ?.label ?? toSentenceCase(eventSubtype);

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
    const success = await deleteAccountingRuleCaller(item.identifier);
    if (success) {
      await fetchData();
    }
  } catch {
    setMessage({
      description: t('accounting_settings.rule.delete_error')
    });
  }
};

const refresh = async () => {
  await fetchData();
  await checkConflicts();
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

const getType = (eventType: string, eventSubtype: string) =>
  getEventTypeData({
    eventType,
    eventSubtype
  });

onMounted(async () => {
  const {
    currentRoute: {
      query: {
        'add-rule': addRule,
        'edit-rule': editRule,
        eventSubtype,
        eventType,
        counterparty
      }
    }
  } = router;

  const ruleData = {
    eventSubtype: eventSubtype?.toString() ?? '',
    eventType: eventType?.toString() ?? '',
    counterparty: counterparty?.toString() ?? null
  };

  if (addRule) {
    set(editableItem, {
      ...getPlaceholderRule(),
      ...ruleData
    });
    setOpenDialog(true);
    await router.replace({ query: {} });
  } else if (editRule) {
    const rule = await getAccountingRule({
      eventTypes: [ruleData.eventType],
      eventSubtypes: [ruleData.eventSubtype],
      counterparties: counterparty ? [ruleData.counterparty] : undefined,
      limit: 1,
      offset: 0
    });
    set(editableItem, rule);
    setOpenDialog(!!rule);
    await router.replace({ query: {} });
  }
  await refresh();
});

const conflictsDialogOpen: Ref<boolean> = ref(false);
</script>

<template>
  <TablePageLayout child :title="[t('accounting_settings.rule.title')]">
    <template #buttons>
      <div class="flex flex-row items-center justify-end gap-2">
        <RuiTooltip :open-delay="400">
          <template #activator>
            <RuiButton
              variant="outlined"
              color="primary"
              :loading="isLoading"
              @click="refresh()"
            >
              <template #prepend>
                <RuiIcon name="refresh-line" />
              </template>
              {{ t('common.refresh') }}
            </RuiButton>
          </template>
          {{ t('accounting_settings.rule.refresh_tooltip') }}
        </RuiTooltip>
        <RuiButton color="primary" @click="add()">
          <template #prepend>
            <RuiIcon name="add-line" />
          </template>
          {{ t('accounting_settings.rule.add') }}
        </RuiButton>
      </div>
    </template>

    <RuiCard>
      <template #custom-header>
        <div class="flex items-center justify-between p-4 pb-0 gap-4">
          <template v-if="conflictsNumber > 0">
            <RuiButton color="warning" @click="conflictsDialogOpen = true">
              <template #prepend>
                <RuiIcon name="error-warning-line" />
              </template>
              {{ t('accounting_settings.rule.conflicts.title') }}
              <template #append>
                <RuiChip
                  size="sm"
                  class="!p-0 !bg-rui-warning-darker"
                  color="warning"
                >
                  {{ conflictsNumber }}
                </RuiChip>
              </template>
            </RuiButton>
            <AccountingRuleConflictsDialog
              v-if="conflictsDialogOpen"
              :table-headers="tableHeaders"
              @close="conflictsDialogOpen = false"
              @refresh="refresh()"
            />
          </template>

          <div class="w-full md:w-[25rem] ml-auto">
            <TableFilter
              :matches="filters"
              :matchers="matchers"
              @update:matches="updateFilter($event)"
            />
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
            <template #header.taxable>
              <RuiTooltip
                :popper="{ placement: 'top' }"
                open-delay="400"
                class="flex items-center"
                tooltip-class="max-w-[10rem]"
              >
                <template #activator>
                  <div class="flex items-center text-left gap-2">
                    <RuiIcon
                      class="shrink-0"
                      size="18"
                      name="information-line"
                    />
                    {{ t('accounting_settings.rule.labels.taxable') }}
                  </div>
                </template>
                {{ t('accounting_settings.rule.labels.taxable_subtitle') }}
              </RuiTooltip>
            </template>
            <template #header.countEntireAmountSpend>
              <RuiTooltip
                :popper="{ placement: 'top' }"
                open-delay="400"
                class="flex items-center"
                tooltip-class="max-w-[10rem]"
              >
                <template #activator>
                  <div class="flex items-center text-left gap-2">
                    <RuiIcon
                      class="shrink-0"
                      size="18"
                      name="information-line"
                    />
                    {{
                      t(
                        'accounting_settings.rule.labels.count_entire_amount_spend'
                      )
                    }}
                  </div>
                </template>
                {{
                  t(
                    'accounting_settings.rule.labels.count_entire_amount_spend_subtitle'
                  )
                }}
              </RuiTooltip>
            </template>
            <template #header.countCostBasisPnl>
              <RuiTooltip
                :popper="{ placement: 'top' }"
                open-delay="400"
                class="flex items-center"
                tooltip-class="max-w-[10rem]"
              >
                <template #activator>
                  <div class="flex items-center text-left gap-2">
                    <RuiIcon
                      class="shrink-0"
                      size="18"
                      name="information-line"
                    />
                    {{
                      t('accounting_settings.rule.labels.count_cost_basis_pnl')
                    }}
                  </div>
                </template>
                {{
                  t(
                    'accounting_settings.rule.labels.count_cost_basis_pnl_subtitle'
                  )
                }}
              </RuiTooltip>
            </template>
            <template #item.eventTypeAndSubtype="{ item }">
              <div>{{ getHistoryEventTypeName(item.eventType) }} -</div>
              <div>{{ getHistoryEventSubTypeName(item.eventSubtype) }}</div>
            </template>
            <template #item.resultingCombination="{ item }">
              <HistoryEventTypeCombination
                :type="getType(item.eventType, item.eventSubtype)"
                show-label
              />
            </template>
            <template #item.counterparty="{ item }">
              <HistoryEventTypeCounterparty
                v-if="item.counterparty"
                text
                :event="{ counterparty: item.counterparty }"
              />
              <span v-else>-</span>
            </template>
            <template #item.taxable="{ item }">
              <AccountingRuleWithLinkedSettingDisplay
                identifier="taxable"
                :item="item.taxable"
              />
            </template>
            <template #item.countEntireAmountSpend="{ item }">
              <AccountingRuleWithLinkedSettingDisplay
                identifier="countEntireAmountSpend"
                :item="item.countEntireAmountSpend"
              />
            </template>
            <template #item.countCostBasisPnl="{ item }">
              <AccountingRuleWithLinkedSettingDisplay
                identifier="countCostBasisPnl"
                :item="item.countCostBasisPnl"
              />
            </template>
            <template #item.accountingTreatment="{ item }">
              <BadgeDisplay v-if="item.accountingTreatment">
                {{ item.accountingTreatment }}
              </BadgeDisplay>
              <span v-else>-</span>
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
  </TablePageLayout>
</template>
