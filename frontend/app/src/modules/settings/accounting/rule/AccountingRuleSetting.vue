<script setup lang="ts">
import AccountingRuleActionDialog from '@/modules/settings/accounting/rule/AccountingRuleActionDialog.vue';
import AccountingRuleConflictsBanner from '@/modules/settings/accounting/rule/AccountingRuleConflictsBanner.vue';
import AccountingRuleFormDialog from '@/modules/settings/accounting/rule/AccountingRuleFormDialog.vue';
import AccountingRuleImportDialog from '@/modules/settings/accounting/rule/AccountingRuleImportDialog.vue';
import AccountingRuleSettingHeader from '@/modules/settings/accounting/rule/AccountingRuleSettingHeader.vue';
import AccountingRuleTable from '@/modules/settings/accounting/rule/AccountingRuleTable.vue';
import AccountingRuleToolbar from '@/modules/settings/accounting/rule/AccountingRuleToolbar.vue';
import { useAccountingRuleConflicts } from '@/modules/settings/accounting/rule/use-accounting-rule-conflicts';
import { useAccountingRuleEditor } from '@/modules/settings/accounting/rule/use-accounting-rule-editor';
import { useAccountingRuleMaintenance } from '@/modules/settings/accounting/rule/use-accounting-rule-maintenance';
import { useAccountingRulesTable } from '@/modules/settings/accounting/rule/use-accounting-rules-table';
import { useRuleEventsLink } from '@/modules/settings/accounting/rule/use-rule-events-link';
import { anchorId } from '@/modules/settings/settings-actions';

const {
  collection,
  filter,
  isLoading,
  matchers,
  modelCustomRuleHandling,
  pagination,
  refetch,
  setFilter,
  showsCustomRules,
} = useAccountingRulesTable();

const { checkConflicts, conflictsNumber, modelConflictsDialogOpen } = useAccountingRuleConflicts();

const {
  actionDialog,
  add,
  applyRouteIntent,
  closeActionDialog,
  edit,
  handleRuleAction,
  modelEditMode,
  modelEventIds,
  modelRule,
} = useAccountingRuleEditor();

const { viewEvents } = useRuleEventsLink();

/** Reloads both things a change can have touched: the rules, and the conflicts between them. */
async function refresh(): Promise<void> {
  await refetch();
  await checkConflicts();
}

const {
  confirmDelete,
  confirmReset,
  exportFileLoading,
  exportJSON,
  importFileLoading,
  modelImportDialogOpen,
  resetLoading,
} = useAccountingRuleMaintenance({ refetch, refresh });

onMounted(async () => {
  await applyRouteIntent();
  await refresh();
});
</script>

<template>
  <div
    :id="anchorId('accountingRule')"
    class="mt-4"
  >
    <AccountingRuleSettingHeader
      :loading="isLoading"
      :export-loading="exportFileLoading"
      :import-loading="importFileLoading"
      :reset-loading="resetLoading"
      @refresh="refresh()"
      @add="add()"
      @export="exportJSON()"
      @import="modelImportDialogOpen = true"
      @reset="confirmReset()"
    />

    <RuiCard class="mt-5">
      <template #custom-header>
        <div class="p-4 pb-0">
          <AccountingRuleConflictsBanner
            v-model:open="modelConflictsDialogOpen"
            :count="conflictsNumber"
            @refresh="refresh()"
          />
          <AccountingRuleToolbar
            v-model:custom-rule-handling="modelCustomRuleHandling"
            :filter="filter"
            :matchers="matchers"
            @update:filter="setFilter($event)"
          />
        </div>
      </template>

      <AccountingRuleTable
        :key="modelCustomRuleHandling"
        v-model:pagination="pagination"
        :state="collection"
        :is-loading="isLoading"
        :is-custom="showsCustomRules"
        @delete-click="confirmDelete($event)"
        @edit-click="edit($event)"
        @view-events-click="viewEvents($event)"
      />

      <AccountingRuleFormDialog
        v-model="modelRule"
        :edit-mode="modelEditMode"
        :event-ids="modelEventIds"
        @refresh="refetch()"
      />

      <AccountingRuleActionDialog
        v-if="actionDialog.open && actionDialog.context"
        :has-event-specific-rule="actionDialog.hasEventSpecificRule"
        :has-general-rule="actionDialog.hasGeneralRule"
        :event-ids="actionDialog.eventIds"
        @close="closeActionDialog()"
        @select="handleRuleAction($event)"
      />

      <AccountingRuleImportDialog
        v-model="modelImportDialogOpen"
        :loading="importFileLoading"
        @refresh="refresh()"
      />
    </RuiCard>
  </div>
</template>
