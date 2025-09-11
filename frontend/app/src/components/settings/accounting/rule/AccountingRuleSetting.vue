<script setup lang="ts">
import type { AccountingRuleEntry, AccountingRuleRequestPayload } from '@/types/settings/accounting';
import { startPromise } from '@shared/utils';
import AccountingRuleConflictsDialog from '@/components/settings/accounting/rule/AccountingRuleConflictsDialog.vue';
import AccountingRuleFormDialog from '@/components/settings/accounting/rule/AccountingRuleFormDialog.vue';
import AccountingRuleImportDialog from '@/components/settings/accounting/rule/AccountingRuleImportDialog.vue';
import AccountingRuleTable from '@/components/settings/accounting/rule/AccountingRuleTable.vue';
import SettingCategoryHeader from '@/components/settings/SettingCategoryHeader.vue';
import TableFilter from '@/components/table-filter/TableFilter.vue';
import { useAccountingApi } from '@/composables/api/settings/accounting-api';
import { type Filters, type Matcher, useAccountingRuleFilter } from '@/composables/filters/accounting-rule';
import { useAccountingSettings } from '@/composables/settings/accounting';
import { usePaginationFilters } from '@/composables/use-pagination-filter';
import { useConfirmStore } from '@/store/confirm';
import { useMessageStore } from '@/store/message';
import { useTaskStore } from '@/store/tasks';
import { TaskType } from '@/types/task-type';
import { getPlaceholderRule } from '@/utils/settings';

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();
const route = useRoute();

const { exportJSON, getAccountingRule, getAccountingRules, getAccountingRulesConflicts } = useAccountingSettings();

const editMode = ref<boolean>(false);
const onlyCustomRules = ref<string>('regular');

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
  extraParams: computed(() => ({
    onlyCustomRules: get(onlyCustomRules) === 'custom',
  })),
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

function add(rule?: AccountingRuleEntry) {
  set(modelValue, rule || createNewEntry());
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

onMounted(async () => {
  const { query } = get(route);
  const { 'add-rule': addRule, counterparty, 'edit-rule': editRule, eventSubtype, eventType } = query;

  const ruleData = {
    counterparty: counterparty?.toString() ?? null,
    eventSubtype: eventSubtype?.toString() ?? '',
    eventType: eventType?.toString() ?? '',
  };

  async function openDialog(rule?: AccountingRuleEntry, forceAdd = false) {
    if (rule) {
      startPromise(nextTick(() => forceAdd ? add(rule) : edit(rule)));
    }
    await router.replace({ query: {} });
  }

  if (addRule) {
    await openDialog({
      ...getPlaceholderRule(),
      ...ruleData,
    }, true);
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

const { useIsTaskRunning } = useTaskStore();

const exportFileLoading = useIsTaskRunning(TaskType.EXPORT_ACCOUNTING_RULES);
const importFileLoading = useIsTaskRunning(TaskType.IMPORT_ACCOUNTING_RULES);

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
        <div class="p-4 pb-0">
          <template v-if="conflictsNumber > 0">
            <RuiButton
              color="warning"
              class="mb-4"
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
              @close="conflictsDialogOpen = false"
              @refresh="refresh()"
            />
          </template>
          <div class="flex flex-wrap gap-x-4 gap-y-2 items-center justify-between">
            <RuiTabs
              v-model="onlyCustomRules"
              color="primary"
              class="border border-default rounded bg-white dark:bg-rui-grey-900 flex max-w-min"
            >
              <RuiTab value="regular">
                {{ t('accounting_settings.rule.tabs.regular') }}
              </RuiTab>
              <RuiTab value="custom">
                {{ t('accounting_settings.rule.tabs.custom') }}
              </RuiTab>
            </RuiTabs>

            <div class="w-full md:w-[25rem] ml-auto">
              <TableFilter
                :matches="filters"
                :matchers="matchers"
                @update:matches="updateFilter($event)"
              />
            </div>
          </div>
        </div>
      </template>

      <AccountingRuleTable
        v-model:pagination="pagination"
        :state="state"
        :is-loading="isLoading"
        :is-custom="onlyCustomRules === 'custom'"
        @set-page="setPage($event)"
        @delete-click="showDeleteConfirmation($event)"
        @edit-click="edit($event)"
      />

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
