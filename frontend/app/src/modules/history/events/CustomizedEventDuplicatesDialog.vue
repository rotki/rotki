<script setup lang="ts">
import { DuplicateHandlingStatus } from '@/modules/history/events/action-types';
import CustomizedEventDuplicatesList from '@/modules/history/events/CustomizedEventDuplicatesList.vue';
import DuplicateRowActions from '@/modules/history/events/DuplicateRowActions.vue';
import { useCustomizedEventDuplicates } from '@/modules/history/events/use-customized-event-duplicates';
import { DuplicatesTab, useCustomizedEventDuplicatesDialog } from '@/modules/history/events/use-customized-event-duplicates-dialog';
import CardTitle from '@/modules/shell/components/CardTitle.vue';

const modelValue = defineModel<boolean>({ default: false });

const { t } = useI18n({ useScope: 'global' });

const {
  autoFixCount,
  autoFixGroupIds,
  fixLoading,
  ignoreLoading,
  ignoredCount,
  ignoredGroupIds,
  manualReviewCount,
  manualReviewGroupIds,
} = useCustomizedEventDuplicates();

function closeDialog(): void {
  set(modelValue, false);
}

const {
  autoFixLoading,
  autoFixRows,
  fixSelected,
  fixSingle,
  ignoreSelected,
  ignoreSingle,
  ignoredLoading,
  ignoredRows,
  initialize,
  manualReviewLoading,
  manualReviewRows,
  modelActiveTab,
  modelSelectedAutoFix,
  modelSelectedIgnored,
  modelSelectedManualReview,
  restoreSelected,
  restoreSingle,
  showInHistoryEvents,
} = useCustomizedEventDuplicatesDialog({ close: closeDialog });

onBeforeMount(async () => {
  await initialize();
});
</script>

<template>
  <RuiDialog
    v-model="modelValue"
    max-width="1000"
  >
    <RuiCard
      content-class="!py-0"
      divide
    >
      <template #custom-header>
        <div class="flex items-center justify-between w-full px-4 py-2">
          <CardTitle>
            {{ t('customized_event_duplicates.dialog.title') }}
          </CardTitle>
          <RuiButton
            variant="text"
            icon
            @click="closeDialog()"
          >
            <RuiIcon name="lu-x" />
          </RuiButton>
        </div>
      </template>

      <RuiTabs
        v-model="modelActiveTab"
        class="border-b border-default"
        color="primary"
      >
        <RuiTab>
          {{ t('customized_event_duplicates.tabs.auto_fix') }}
          <RuiChip
            v-if="autoFixCount > 0"
            color="primary"
            size="sm"
            class="ml-2 !px-0.5 !py-0"
          >
            {{ autoFixCount }}
          </RuiChip>
        </RuiTab>
        <RuiTab>
          {{ t('customized_event_duplicates.tabs.manual_review') }}
          <RuiChip
            v-if="manualReviewCount > 0"
            color="warning"
            size="sm"
            class="ml-2 !px-0.5 !py-0"
          >
            {{ manualReviewCount }}
          </RuiChip>
        </RuiTab>
        <RuiTab>
          {{ t('customized_event_duplicates.tabs.non_duplicated') }}
          <RuiChip
            v-if="ignoredCount > 0"
            color="secondary"
            size="sm"
            class="ml-2 !px-0.5 !py-0"
          >
            {{ ignoredCount }}
          </RuiChip>
        </RuiTab>
      </RuiTabs>

      <RuiTabItems
        v-model="modelActiveTab"
        class="my-4"
      >
        <RuiTabItem>
          <CustomizedEventDuplicatesList
            v-model:selected="modelSelectedAutoFix"
            :description="t('customized_event_duplicates.dialog.auto_fix_description')"
            :rows="autoFixRows"
            :loading="autoFixLoading"
            @show-in-history="showInHistoryEvents(autoFixGroupIds, DuplicateHandlingStatus.AUTO_FIX)"
          >
            <template #actions="{ row }">
              <DuplicateRowActions
                mode="auto-fix"
                :fix-loading="fixLoading"
                :ignore-loading="ignoreLoading"
                @fix="fixSingle(row.groupIdentifier)"
                @ignore="ignoreSingle(row.groupIdentifier)"
              />
            </template>
          </CustomizedEventDuplicatesList>
        </RuiTabItem>

        <RuiTabItem>
          <CustomizedEventDuplicatesList
            v-model:selected="modelSelectedManualReview"
            :description="t('customized_event_duplicates.dialog.manual_review_description')"
            :rows="manualReviewRows"
            :loading="manualReviewLoading"
            @show-in-history="showInHistoryEvents(manualReviewGroupIds, DuplicateHandlingStatus.MANUAL_REVIEW)"
          >
            <template #actions="{ row }">
              <DuplicateRowActions
                mode="manual-review"
                :ignore-loading="ignoreLoading"
                @ignore="ignoreSingle(row.groupIdentifier)"
              />
            </template>
          </CustomizedEventDuplicatesList>
        </RuiTabItem>

        <RuiTabItem>
          <CustomizedEventDuplicatesList
            v-model:selected="modelSelectedIgnored"
            :description="t('customized_event_duplicates.dialog.non_duplicated_description')"
            :rows="ignoredRows"
            :loading="ignoredLoading"
            @show-in-history="showInHistoryEvents(ignoredGroupIds, DuplicateHandlingStatus.IGNORED)"
          >
            <template #actions="{ row }">
              <DuplicateRowActions
                mode="ignored"
                :ignore-loading="ignoreLoading"
                @restore="restoreSingle(row.groupIdentifier)"
              />
            </template>
          </CustomizedEventDuplicatesList>
        </RuiTabItem>
      </RuiTabItems>

      <div class="w-full flex justify-between gap-2 pb-4">
        <div
          v-if="modelActiveTab === DuplicatesTab.AUTO_FIX"
          class="flex gap-2"
        >
          <RuiButton
            variant="outlined"
            color="primary"
            data-testid="fix-selected"
            :disabled="modelSelectedAutoFix.length === 0 || fixLoading"
            :loading="fixLoading"
            @click="fixSelected()"
          >
            <template #prepend>
              <RuiIcon
                size="16"
                name="lu-wand-sparkles"
              />
            </template>
            {{ t('customized_event_duplicates.actions.fix_selected') }}
            <RuiChip
              v-if="modelSelectedAutoFix.length > 0"
              size="sm"
              color="primary"
              class="ml-2 !py-0"
            >
              {{ modelSelectedAutoFix.length }}
            </RuiChip>
          </RuiButton>
          <RuiButton
            variant="outlined"
            data-testid="ignore-selected"
            :disabled="modelSelectedAutoFix.length === 0 || ignoreLoading"
            :loading="ignoreLoading"
            @click="ignoreSelected()"
          >
            <template #prepend>
              <RuiIcon
                size="16"
                name="lu-eye-off"
              />
            </template>
            {{ t('customized_event_duplicates.actions.mark_non_duplicated_selected') }}
          </RuiButton>
        </div>
        <div
          v-else-if="modelActiveTab === DuplicatesTab.MANUAL_REVIEW"
          class="flex gap-2"
        >
          <RuiButton
            variant="outlined"
            data-testid="ignore-selected"
            :disabled="modelSelectedManualReview.length === 0 || ignoreLoading"
            :loading="ignoreLoading"
            @click="ignoreSelected()"
          >
            <template #prepend>
              <RuiIcon
                size="16"
                name="lu-eye-off"
              />
            </template>
            {{ t('customized_event_duplicates.actions.mark_non_duplicated_selected') }}
            <RuiChip
              v-if="modelSelectedManualReview.length > 0"
              size="sm"
              color="primary"
              class="ml-2 !py-0"
            >
              {{ modelSelectedManualReview.length }}
            </RuiChip>
          </RuiButton>
        </div>
        <div
          v-else
          class="flex gap-2"
        >
          <RuiButton
            variant="outlined"
            color="primary"
            data-testid="restore-selected"
            :disabled="modelSelectedIgnored.length === 0 || ignoreLoading"
            :loading="ignoreLoading"
            @click="restoreSelected()"
          >
            <template #prepend>
              <RuiIcon
                size="16"
                name="lu-rotate-ccw"
              />
            </template>
            {{ t('customized_event_duplicates.actions.restore_selected') }}
            <RuiChip
              v-if="modelSelectedIgnored.length > 0"
              size="sm"
              color="primary"
              class="ml-2 !py-0"
            >
              {{ modelSelectedIgnored.length }}
            </RuiChip>
          </RuiButton>
        </div>
        <RuiButton
          variant="text"
          data-testid="close-dialog"
          @click="closeDialog()"
        >
          {{ t('common.actions.close') }}
        </RuiButton>
      </div>
    </RuiCard>
  </RuiDialog>
</template>
