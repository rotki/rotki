<script setup lang="ts">
import type { DataTableColumn } from '@rotki/ui-library-compat';
import type { Collection } from '@/types/collection';
import type {
  Filters,
  Matcher,
} from '@/composables/filters/accounting-rule';
import type {
  AccountingRuleEntry,
  AccountingRuleRequestPayload,
} from '@/types/settings/accounting';

const { t } = useI18n();
const router = useRouter();

const { getAccountingRule, getAccountingRules, getAccountingRulesConflicts } = useAccountingSettings();

const {
  state,
  isLoading,
  fetchData,
  setPage,
  filters,
  pagination,
  matchers,
  updateFilter,
  editableItem,
} = usePaginationFilters<
  AccountingRuleEntry,
  AccountingRuleRequestPayload,
  AccountingRuleEntry,
  Collection<AccountingRuleEntry>,
  Filters,
  Matcher
>(null, true, useAccountingRuleFilter, getAccountingRules);

const conflictsNumber: Ref<number> = ref(0);

const conflictsDialogOpen: Ref<boolean> = ref(false);

async function checkConflicts() {
  const { total } = await getAccountingRulesConflicts({ limit: 1, offset: 0 });
  set(conflictsNumber, total);

  const {
    currentRoute: {
      query: { resolveConflicts },
    },
  } = router;

  if (resolveConflicts) {
    if (total > 0)
      set(conflictsDialogOpen, true);

    await router.replace({ query: {} });
  }
}

const tableHeaders = computed<DataTableColumn[]>(() => [
  {
    label: `${t('accounting_settings.rule.labels.event_type')} - \n${t(
      'accounting_settings.rule.labels.event_subtype',
    )}`,
    key: 'eventTypeAndSubtype',
    class: 'whitespace-pre-line',
    cellClass: 'py-4',
  },
  {
    label: t('transactions.events.form.resulting_combination.label'),
    key: 'resultingCombination',
  },
  {
    label: t('common.counterparty'),
    key: 'counterparty',
    class: 'border-r border-default',
    cellClass: 'border-r border-default',
  },
  {
    label: t('accounting_settings.rule.labels.taxable'),
    key: 'taxable',
    class: 'max-w-[6rem] text-sm whitespace-normal font-medium align-center',
    align: 'center',
  },
  {
    label: t('accounting_settings.rule.labels.count_entire_amount_spend'),
    key: 'countEntireAmountSpend',
    class: 'max-w-[6rem] text-sm whitespace-normal font-medium align-center',
    align: 'center',
  },
  {
    label: t('accounting_settings.rule.labels.count_cost_basis_pnl'),
    key: 'countCostBasisPnl',
    class: 'max-w-[6rem] text-sm whitespace-normal font-medium align-center',
    align: 'center',
  },
  {
    label: t('accounting_settings.rule.labels.accounting_treatment'),
    key: 'accountingTreatment',
    class: 'max-w-[6rem] text-sm whitespace-normal font-medium align-center',
  },
  {
    label: t('common.actions_text'),
    key: 'actions',
    align: 'center',
    width: '1px',
  },
]);

const { historyEventTypesData, historyEventSubTypesData, getEventTypeData } = useHistoryEventMappings();

function getHistoryEventTypeName(eventType: string): string {
  return get(historyEventTypesData).find(item => item.identifier === eventType)
    ?.label ?? toSentenceCase(eventType);
}

function getHistoryEventSubTypeName(eventSubtype: string): string {
  return get(historyEventSubTypesData).find(item => item.identifier === eventSubtype)
    ?.label ?? toSentenceCase(eventSubtype);
}

const { setOpenDialog, setPostSubmitFunc } = useAccountingRuleForm();

function add() {
  set(editableItem, null);
  setOpenDialog(true);
}

function edit(rule: AccountingRuleEntry) {
  set(editableItem, rule);
  setOpenDialog(true);
}

setPostSubmitFunc(fetchData);

const { show } = useConfirmStore();
const { setMessage } = useMessageStore();

const { deleteAccountingRule: deleteAccountingRuleCaller } = useAccountingApi();

async function deleteAccountingRule(item: AccountingRuleEntry) {
  try {
    const success = await deleteAccountingRuleCaller(item.identifier);
    if (success)
      await fetchData();
  }
  catch {
    setMessage({
      description: t('accounting_settings.rule.delete_error'),
    });
  }
}

async function refresh() {
  await fetchData();
  await checkConflicts();
}

function showDeleteConfirmation(item: AccountingRuleEntry) {
  show(
    {
      title: t('accounting_settings.rule.delete'),
      message: t('accounting_settings.rule.confirm_delete'),
    },
    async () => await deleteAccountingRule(item),
  );
}

function getType(eventType: string, eventSubtype: string) {
  return get(
    getEventTypeData({
      eventType,
      eventSubtype,
    }),
  );
}

onMounted(async () => {
  const {
    currentRoute: {
      query: {
        'add-rule': addRule,
        'edit-rule': editRule,
        eventSubtype,
        eventType,
        counterparty,
      },
    },
  } = router;

  const ruleData = {
    eventSubtype: eventSubtype?.toString() ?? '',
    eventType: eventType?.toString() ?? '',
    counterparty: counterparty?.toString() ?? null,
  };

  if (addRule) {
    set(editableItem, {
      ...getPlaceholderRule(),
      ...ruleData,
    });
    setOpenDialog(true);
    await router.replace({ query: {} });
  }
  else if (editRule) {
    const rule = await getAccountingRule(
      {
        eventTypes: [ruleData.eventType],
        eventSubtypes: [ruleData.eventSubtype],
        limit: 2,
        offset: 0,
      },
      ruleData.counterparty,
    );
    set(editableItem, rule);
    setOpenDialog(!!rule);
    await router.replace({ query: {} });
  }
  await refresh();
});
</script>

<template>
  <TablePageLayout
    child
    :title="[t('accounting_settings.rule.title')]"
  >
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
        <RuiButton
          color="primary"
          @click="add()"
        >
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
            <RuiButton
              color="warning"
              @click="conflictsDialogOpen = true"
            >
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

      <CollectionHandler
        :collection="state"
        @set-page="setPage($event)"
      >
        <template #default="{ data }">
          <RuiDataTable
            outlined
            :rows="data"
            :cols="tableHeaders"
            :loading="isLoading"
            :pagination.sync="pagination"
            row-attr="identifier"
            :pagination-modifiers="{ external: true }"
          >
            <template #header.taxable>
              <RuiTooltip
                :popper="{ placement: 'top' }"
                :open-delay="400"
                class="flex items-center h-full"
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
                :open-delay="400"
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
                        'accounting_settings.rule.labels.count_entire_amount_spend',
                      )
                    }}
                  </div>
                </template>
                {{
                  t(
                    'accounting_settings.rule.labels.count_entire_amount_spend_subtitle',
                  )
                }}
              </RuiTooltip>
            </template>
            <template #header.countCostBasisPnl>
              <RuiTooltip
                :popper="{ placement: 'top' }"
                :open-delay="400"
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
                    'accounting_settings.rule.labels.count_cost_basis_pnl_subtitle',
                  )
                }}
              </RuiTooltip>
            </template>
            <template #header.accountingTreatment>
              <div class="max-w-[5rem] text-sm whitespace-normal font-medium">
                {{ t('accounting_settings.rule.labels.accounting_treatment') }}
              </div>
            </template>
            <template #item.eventTypeAndSubtype="{ row }">
              <div>{{ getHistoryEventTypeName(row.eventType) }} -</div>
              <div>{{ getHistoryEventSubTypeName(row.eventSubtype) }}</div>
            </template>
            <template #item.resultingCombination="{ row }">
              <HistoryEventTypeCombination
                :type="getType(row.eventType, row.eventSubtype)"
                show-label
              />
            </template>
            <template #item.counterparty="{ row }">
              <CounterpartyDisplay
                v-if="row.counterparty"
                :counterparty="row.counterparty"
              />
              <span v-else>-</span>
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
              <BadgeDisplay v-if="row.accountingTreatment">
                {{ row.accountingTreatment }}
              </BadgeDisplay>
              <span v-else>-</span>
            </template>
            <template #item.actions="{ row }">
              <RowActions
                :delete-tooltip="t('accounting_settings.rule.delete')"
                :edit-tooltip="t('accounting_settings.rule.edit')"
                @delete-click="showDeleteConfirmation(row)"
                @edit-click="edit(row)"
              />
            </template>
          </RuiDataTable>
        </template>
      </CollectionHandler>
    </RuiCard>
    <AccountingRuleFormDialog
      :loading="isLoading"
      :editable-item="editableItem"
    />
  </TablePageLayout>
</template>
