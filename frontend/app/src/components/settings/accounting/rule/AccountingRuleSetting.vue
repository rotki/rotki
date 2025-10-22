<script setup lang="ts">
import type {
  AccountingRuleAction,
  AccountingRuleEntry,
  AccountingRuleRequestPayload,
} from '@/types/settings/accounting';
import { z } from 'zod/v4';
import AccountingRuleActionDialog, { type Props as AccountingRuleActionDialogProps } from '@/components/settings/accounting/rule/AccountingRuleActionDialog.vue';
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

const CUSTOM_RULE_HANDLING = {
  /** Show regular rules (exclude event-specific rules) */
  EXCLUDE: 'exclude',
  /** Show only event-specific rules */
  ONLY: 'only',
} as const;

type CustomRuleHandling = typeof CUSTOM_RULE_HANDLING[keyof typeof CUSTOM_RULE_HANDLING];

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
const customRuleHandling = ref<CustomRuleHandling>(CUSTOM_RULE_HANDLING.EXCLUDE);

const modelValue = ref<AccountingRuleEntry>();
const eventIdsForRule = ref<number[]>();
const actionDialog = ref<boolean>(false);
const actionDialogProps = ref<AccountingRuleActionDialogProps>();

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
    set(actionDialogProps, {
      eventId: eventIdNum,
      hasEventSpecificRule: false,
      hasGeneralRule: false,
    });
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

  set(actionDialogProps, {
    eventId: eventIdNum,
    eventIds: eventSpecificRule?.eventIds ?? undefined,
    eventSpecificRule,
    generalRule,
    hasEventSpecificRule,
    hasGeneralRule,
  });
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
  const props = get(actionDialogProps);
  if (!props)
    return;

  const { eventId, eventSpecificRule, generalRule } = props;

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
              v-model="customRuleHandling"
              color="primary"
              class="border border-default rounded bg-white dark:bg-rui-grey-900 flex max-w-min"
            >
              <RuiTab :value="CUSTOM_RULE_HANDLING.EXCLUDE">
                {{ t('accounting_settings.rule.tabs.regular') }}
              </RuiTab>
              <RuiTab :value="CUSTOM_RULE_HANDLING.ONLY">
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
        :is-custom="customRuleHandling === CUSTOM_RULE_HANDLING.ONLY"
        @set-page="setPage($event)"
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
        v-if="actionDialog && actionDialogProps"
        v-bind="actionDialogProps"
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
