<script setup lang="ts">
import type { AccountingRuleEntry, AccountingRuleRequestPayload } from '@/types/settings/accounting';
import type { DataTableColumn } from '@rotki/ui-library';
import CollectionHandler from '@/components/helper/CollectionHandler.vue';
import RowActions from '@/components/helper/RowActions.vue';
import BadgeDisplay from '@/components/history/BadgeDisplay.vue';
import CounterpartyDisplay from '@/components/history/CounterpartyDisplay.vue';
import HistoryEventTypeCombination from '@/components/history/events/HistoryEventTypeCombination.vue';
import AccountingRuleConflictsDialog from '@/components/settings/accounting/rule/AccountingRuleConflictsDialog.vue';
import AccountingRuleFormDialog from '@/components/settings/accounting/rule/AccountingRuleFormDialog.vue';
import AccountingRuleImportDialog from '@/components/settings/accounting/rule/AccountingRuleImportDialog.vue';
import AccountingRuleWithLinkedSettingDisplay
  from '@/components/settings/accounting/rule/AccountingRuleWithLinkedSettingDisplay.vue';
import SettingCategoryHeader from '@/components/settings/SettingCategoryHeader.vue';
import TableFilter from '@/components/table-filter/TableFilter.vue';
import { useAccountingApi } from '@/composables/api/settings/accounting-api';
import { type Filters, type Matcher, useAccountingRuleFilter } from '@/composables/filters/accounting-rule';
import { useHistoryEventMappings } from '@/composables/history/events/mapping';
import { useAccountingSettings } from '@/composables/settings/accounting';
import { usePaginationFilters } from '@/composables/use-pagination-filter';
import { useConfirmStore } from '@/store/confirm';
import { useMessageStore } from '@/store/message';
import { useTaskStore } from '@/store/tasks';
import { TaskType } from '@/types/task-type';
import { getPlaceholderRule } from '@/utils/settings';
import { startPromise } from '@shared/utils';

const { t } = useI18n();
const router = useRouter();
const route = useRoute();

const { exportJSON, getAccountingRule, getAccountingRules, getAccountingRulesConflicts } = useAccountingSettings();

const editMode = ref<boolean>(false);

const modelValue = ref<AccountingRuleEntry>();

const {
  fetchData,
  filters,
  isLoading,
  matchers,
  pagination,
  setPage,
  state,
  updateFilter,
} = usePaginationFilters<
  AccountingRuleEntry,
  AccountingRuleRequestPayload,
  Filters,
  Matcher
>(getAccountingRules, {
  filterSchema: useAccountingRuleFilter,
  history: 'router',
});

const conflictsNumber = ref<number>(0);

const conflictsDialogOpen = ref<boolean>(false);

async function checkConflicts() {
  const { total } = await getAccountingRulesConflicts({ limit: 1, offset: 0 });
  set(conflictsNumber, total);

  const { currentRoute } = router;

  const {
    query: { resolveConflicts },
  } = get(currentRoute);

  if (resolveConflicts) {
    if (total > 0)
      set(conflictsDialogOpen, true);

    await router.replace({ query: {} });
  }
}

const cols = computed<DataTableColumn<AccountingRuleEntry>[]>(() => [
  {
    cellClass: 'py-4',
    class: 'whitespace-pre-line',
    key: 'eventTypeAndSubtype',
    label: `${t('accounting_settings.rule.labels.event_type')} - \n${t(
      'accounting_settings.rule.labels.event_subtype',
    )}`,
  },
  {
    key: 'resultingCombination',
    label: t('transactions.events.form.resulting_combination.label'),
  },
  {
    cellClass: 'border-r border-default',
    class: 'border-r border-default',
    key: 'counterparty',
    label: t('common.counterparty'),
  },
  {
    align: 'center',
    class: 'max-w-[6rem] text-sm whitespace-normal font-medium align-center',
    key: 'taxable',
    label: t('accounting_settings.rule.labels.taxable'),
  },
  {
    align: 'center',
    class: 'max-w-[6rem] text-sm whitespace-normal font-medium align-center',
    key: 'countEntireAmountSpend',
    label: t('accounting_settings.rule.labels.count_entire_amount_spend'),
  },
  {
    align: 'center',
    class: 'max-w-[6rem] text-sm whitespace-normal font-medium align-center',
    key: 'countCostBasisPnl',
    label: t('accounting_settings.rule.labels.count_cost_basis_pnl'),
  },
  {
    class: 'max-w-[6rem] text-sm whitespace-normal font-medium align-center',
    key: 'accountingTreatment',
    label: t('accounting_settings.rule.labels.accounting_treatment'),
  },
  {
    align: 'center',
    key: 'actions',
    label: t('common.actions_text'),
    width: '1px',
  },
]);

const { getEventTypeData, historyEventSubTypesData, historyEventTypesData } = useHistoryEventMappings();

function getHistoryEventTypeName(eventType: string): string {
  return get(historyEventTypesData).find(item => item.identifier === eventType)?.label ?? toSentenceCase(eventType);
}

function getHistoryEventSubTypeName(eventSubtype: string): string {
  return (
    get(historyEventSubTypesData).find(item => item.identifier === eventSubtype)?.label
    ?? toSentenceCase(eventSubtype)
  );
}

function createNewEntry() {
  return (
    {
      accountingTreatment: null,
      countCostBasisPnl: {
        value: false,
      },
      countEntireAmountSpend: {
        value: false,
      },
      counterparty: null,
      eventSubtype: '',
      eventType: '',
      identifier: -1,
      taxable: {
        value: false,
      },
    }
  );
}

function add() {
  set(modelValue, createNewEntry());
  set(editMode, false);
}

function edit(rule: AccountingRuleEntry) {
  set(modelValue, rule);
  set(editMode, true);
}

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
      message: t('accounting_settings.rule.confirm_delete'),
      title: t('accounting_settings.rule.delete'),
    },
    async () => await deleteAccountingRule(item),
  );
}

function getType(eventType: string, eventSubtype: string) {
  return get(
    getEventTypeData({
      eventSubtype,
      eventType,
    }),
  );
}

onMounted(async () => {
  const { query } = get(route);
  const { 'add-rule': addRule, counterparty, 'edit-rule': editRule, eventSubtype, eventType } = query;

  const ruleData = {
    counterparty: counterparty?.toString() ?? null,
    eventSubtype: eventSubtype?.toString() ?? '',
    eventType: eventType?.toString() ?? '',
  };

  async function openDialog(rule?: AccountingRuleEntry) {
    if (rule) {
      startPromise(nextTick(() => {
        edit(rule);
      }));
    }
    await router.replace({ query: {} });
  }

  if (addRule) {
    await openDialog({
      ...getPlaceholderRule(),
      ...ruleData,
    });
  }
  else if (editRule) {
    await openDialog(await getAccountingRule({
      eventSubtypes: [ruleData.eventSubtype],
      eventTypes: [ruleData.eventType],
      limit: 2,
      offset: 0,
    }, ruleData.counterparty));
  }
  await refresh();
});

const { isTaskRunning } = useTaskStore();

const exportFileLoading = isTaskRunning(TaskType.EXPORT_ACCOUNTING_RULES);
const importFileLoading = isTaskRunning(TaskType.IMPORT_ACCOUNTING_RULES);

const importFileDialog = ref<boolean>(false);
</script>

<template>
  <div>
    <div class="pb-5 border-b border-default flex flex-wrap gap-2 items-center justify-between">
      <SettingCategoryHeader>
        <template #title>
          {{ t('accounting_settings.rule.title') }}
        </template>
        <template #subtitle>
          {{ t('accounting_settings.rule.subtitle') }}
        </template>
      </SettingCategoryHeader>
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
                <RuiIcon name="lu-refresh-ccw" />
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
            <RuiIcon name="lu-plus" />
          </template>
          {{ t('accounting_settings.rule.add') }}
        </RuiButton>
        <RuiMenu
          :popper="{ placement: 'bottom-end' }"
          close-on-content-click
        >
          <template #activator="{ attrs }">
            <RuiButton
              variant="text"
              icon
              size="sm"
              class="!p-2"
              v-bind="attrs"
            >
              <RuiIcon
                name="lu-ellipsis-vertical"
                size="20"
              />
            </RuiButton>
          </template>
          <div class="py-2">
            <RuiButton
              variant="list"
              :loading="exportFileLoading"
              @click="exportJSON()"
            >
              <template #prepend>
                <RuiIcon name="lu-file-down" />
              </template>
              {{ t('accounting_settings.rule.export') }}
            </RuiButton>
            <RuiButton
              variant="list"
              :loading="importFileLoading"
              @click="importFileDialog = true"
            >
              <template #prepend>
                <RuiIcon name="lu-file-up" />
              </template>
              {{ t('accounting_settings.rule.import') }}
            </RuiButton>
          </div>
        </RuiMenu>
      </div>
    </div>

    <RuiCard class="mt-5">
      <template #custom-header>
        <div class="flex flex-wrap gap-x-4 gap-y-2 items-center justify-between p-4 pb-0">
          <template v-if="conflictsNumber > 0">
            <RuiButton
              color="warning"
              @click="conflictsDialogOpen = true"
            >
              <template #prepend>
                <RuiIcon name="lu-circle-alert" />
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
              :table-headers="cols"
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
            v-model:pagination.external="pagination"
            outlined
            :rows="data"
            :cols="cols"
            :loading="isLoading"
            row-attr="identifier"
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
                      name="lu-info"
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
                      name="lu-info"
                    />
                    {{ t('accounting_settings.rule.labels.count_entire_amount_spend') }}
                  </div>
                </template>
                {{ t('accounting_settings.rule.labels.count_entire_amount_spend_subtitle') }}
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
                      name="lu-info"
                    />
                    {{ t('accounting_settings.rule.labels.count_cost_basis_pnl') }}
                  </div>
                </template>
                {{ t('accounting_settings.rule.labels.count_cost_basis_pnl_subtitle') }}
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

      <AccountingRuleFormDialog
        v-model="modelValue"
        :edit-mode="editMode"
        @refresh="fetchData()"
      />

      <AccountingRuleImportDialog
        v-model="importFileDialog"
        :loading="importFileLoading"
        @refresh="refresh()"
      />
    </RuiCard>
  </div>
</template>
