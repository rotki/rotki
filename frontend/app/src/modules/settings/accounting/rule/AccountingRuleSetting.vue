<script setup lang="ts">
import type {
  AccountingRuleAction,
  AccountingRuleEntry,
  AccountingRuleRequestPayload,
} from '@/modules/settings/types/accounting';
import { z } from 'zod/v4';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';
import { useMessageStore } from '@/modules/core/common/use-message-store';
import { type Filters, type Matcher, useAccountingRuleFilter } from '@/modules/core/table/filters/use-accounting-rule-filter';
import TableFilter from '@/modules/core/table/TableFilter.vue';
import { usePaginationFilters } from '@/modules/core/table/use-pagination-filter';
import { TaskType } from '@/modules/core/tasks/task-type';
import { useTaskStore } from '@/modules/core/tasks/use-task-store';
import AccountingRuleActionDialog, { type ActionDialogContext } from '@/modules/settings/accounting/rule/AccountingRuleActionDialog.vue';
import AccountingRuleConflictsDialog from '@/modules/settings/accounting/rule/AccountingRuleConflictsDialog.vue';
import AccountingRuleFormDialog from '@/modules/settings/accounting/rule/AccountingRuleFormDialog.vue';
import AccountingRuleImportDialog from '@/modules/settings/accounting/rule/AccountingRuleImportDialog.vue';
import AccountingRuleTable from '@/modules/settings/accounting/rule/AccountingRuleTable.vue';
import { useAccountingSettings } from '@/modules/settings/accounting/use-accounting-settings';
import { useAccountingApi } from '@/modules/settings/api/use-accounting-api';
import { SettingsHighlightIds } from '@/modules/settings/setting-highlight-ids';
import SettingCategoryHeader from '@/modules/settings/SettingCategoryHeader.vue';
import { getPlaceholderRule } from '@/modules/settings/settings-utils';

const CustomRuleHandling = {
  /** Show regular rules (exclude event-specific rules) */
  EXCLUDE: 'exclude',
  /** Show only event-specific rules */
  ONLY: 'only',
} as const;

type CustomRuleHandling = typeof CustomRuleHandling[keyof typeof CustomRuleHandling];

const AccountingRuleQuerySchema = z.object({
  counterparty: z.string().nullable().default(null),
  eventSubtype: z.string().default(''),
  eventType: z.string().default(''),
});

type AccountingRuleQuery = z.infer<typeof AccountingRuleQuerySchema>;

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();
const route = useRoute();

const { exportJSON, getAccountingRule, getAccountingRules, getAccountingRulesConflicts } = useAccountingSettings();

const editMode = ref<boolean>(false);
const customRuleHandling = ref<CustomRuleHandling>(CustomRuleHandling.EXCLUDE);

const modelValue = ref<AccountingRuleEntry>();
const eventIdsForRule = ref<number[]>();
const actionDialog = ref<boolean>(false);
const actionDialogContext = ref<ActionDialogContext>();
const actionDialogHasEventSpecific = ref<boolean>(false);
const actionDialogHasGeneral = ref<boolean>(false);
const actionDialogEventIds = ref<number[]>();

const {
  fetchData,
  filters,
  isLoading,
  matchers,
  pagination,
  state,
  updateFilter,
} = usePaginationFilters<
  AccountingRuleEntry,
  AccountingRuleRequestPayload,
  Filters,
  Matcher
>(getAccountingRules, {
  extraParams: computed(() => ({
    customRuleHandling: get(customRuleHandling),
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

function add(rule?: AccountingRuleEntry, eventIds?: number[]) {
  set(modelValue, rule || createNewEntry());
  set(editMode, false);
  set(eventIdsForRule, eventIds);
}

function edit(rule: AccountingRuleEntry, eventIds?: number[]) {
  set(modelValue, rule);
  set(editMode, true);
  set(eventIdsForRule, eventIds);
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

function parseRuleQuery(): AccountingRuleQuery {
  const { query } = get(route);
  return AccountingRuleQuerySchema.parse({
    counterparty: query.counterparty,
    eventSubtype: query.eventSubtype,
    eventType: query.eventType,
  });
}

function addRuleFromQuery(eventIds?: number[]): void {
  const ruleQuery = parseRuleQuery();
  add({
    ...getPlaceholderRule(),
    ...ruleQuery,
  }, eventIds);
}

async function handleAddRule(eventIdNum?: number): Promise<void> {
  if (eventIdNum) {
    set(actionDialogContext, { eventId: eventIdNum });
    set(actionDialogHasEventSpecific, false);
    set(actionDialogHasGeneral, false);
    set(actionDialogEventIds, undefined);
    set(actionDialog, true);
    return;
  }

  addRuleFromQuery();
  await router.replace({ query: {} });
}

async function handleEditRuleWithEventId(eventIdNum: number, ruleQuery: AccountingRuleQuery): Promise<void> {
  const [generalRule, eventSpecificRules] = await Promise.all([
    getAccountingRule({
      eventSubtypes: [ruleQuery.eventSubtype],
      eventTypes: [ruleQuery.eventType],
      limit: 2,
      offset: 0,
    }, ruleQuery.counterparty),
    getAccountingRules({
      eventIds: [eventIdNum],
      limit: 10,
      offset: 0,
    }),
  ]);

  const eventSpecificRule = eventSpecificRules.data.length > 0 ? eventSpecificRules.data[0] : undefined;
  const hasEventSpecificRule = !!eventSpecificRule;
  const hasGeneralRule = !!generalRule;

  set(actionDialogContext, {
    eventId: eventIdNum,
    eventSpecificRule,
    generalRule,
  });
  set(actionDialogHasEventSpecific, hasEventSpecificRule);
  set(actionDialogHasGeneral, hasGeneralRule);
  set(actionDialogEventIds, eventSpecificRule?.eventIds ?? undefined);
  set(actionDialog, true);
}

async function handleEditRuleWithoutEventId(ruleQuery: AccountingRuleQuery): Promise<void> {
  const rule = await getAccountingRule({
    eventSubtypes: [ruleQuery.eventSubtype],
    eventTypes: [ruleQuery.eventType],
    limit: 2,
    offset: 0,
  }, ruleQuery.counterparty);

  if (rule)
    edit(rule);

  await router.replace({ query: {} });
}

async function handleEditRule(eventIdNum: number | undefined, ruleQuery: AccountingRuleQuery): Promise<void> {
  if (eventIdNum) {
    await handleEditRuleWithEventId(eventIdNum, ruleQuery);
    return;
  }

  await handleEditRuleWithoutEventId(ruleQuery);
}

async function handleRuleAction(action: AccountingRuleAction) {
  const ctx = get(actionDialogContext);
  if (!ctx)
    return;

  const { eventId, eventSpecificRule, generalRule } = ctx;

  switch (action) {
    case 'add-general':
      addRuleFromQuery();
      break;
    case 'add-event-specific':
      addRuleFromQuery([eventId]);
      break;
    case 'edit-general':
      if (generalRule)
        edit(generalRule);
      break;
    case 'edit-event-specific':
      if (eventSpecificRule)
        edit(eventSpecificRule, eventSpecificRule.eventIds ?? undefined);
      break;
  }

  set(actionDialog, false);
  await router.replace({ query: {} });
}

onMounted(async () => {
  const { query } = get(route);
  const { 'add-rule': addRule, 'edit-rule': editRule, eventId } = query;

  const ruleQuery = parseRuleQuery();
  const eventIdNum = eventId ? Number(eventId) : undefined;

  if (addRule) {
    await handleAddRule(eventIdNum);
  }
  else if (editRule) {
    await handleEditRule(eventIdNum, ruleQuery);
  }

  await refresh();
});

const { useIsTaskRunning } = useTaskStore();

const exportFileLoading = useIsTaskRunning(TaskType.EXPORT_ACCOUNTING_RULES);
const importFileLoading = useIsTaskRunning(TaskType.IMPORT_ACCOUNTING_RULES);

const importFileDialog = ref<boolean>(false);
</script>

<template>
  <div
    :id="SettingsHighlightIds.ACCOUNTING_RULE"
    class="mt-4"
  >
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
              v-model="customRuleHandling"
              color="primary"
              class="border border-default rounded bg-white dark:bg-rui-grey-900 flex max-w-min"
            >
              <RuiTab :value="CustomRuleHandling.EXCLUDE">
                {{ t('accounting_settings.rule.tabs.regular') }}
              </RuiTab>
              <RuiTab :value="CustomRuleHandling.ONLY">
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
        :key="customRuleHandling"
        v-model:pagination="pagination"
        :state="state"
        :is-loading="isLoading"
        :is-custom="customRuleHandling === CustomRuleHandling.ONLY"
        @delete-click="showDeleteConfirmation($event)"
        @edit-click="edit($event)"
      />

      <AccountingRuleFormDialog
        v-model="modelValue"
        :edit-mode="editMode"
        :event-ids="eventIdsForRule"
        @refresh="fetchData()"
      />

      <AccountingRuleActionDialog
        v-if="actionDialog && actionDialogContext"
        :has-event-specific-rule="actionDialogHasEventSpecific"
        :has-general-rule="actionDialogHasGeneral"
        :event-ids="actionDialogEventIds"
        @close="actionDialog = false"
        @select="handleRuleAction($event)"
      />

      <AccountingRuleImportDialog
        v-model="importFileDialog"
        :loading="importFileLoading"
        @refresh="refresh()"
      />
    </RuiCard>
  </div>
</template>
