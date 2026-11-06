<script setup lang="ts">
import { DuplicateHandlingStatus } from '@/modules/history/events/action-types';
import CustomizedEventDuplicatesFooter from '@/modules/history/events/CustomizedEventDuplicatesFooter.vue';
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
  autoFixActionFailure,
  autoFixError,
  autoFixLoading,
  autoFixRows,
  fixSelected,
  fixSingle,
  ignoreSelected,
  ignoreSingle,
  ignoredActionFailure,
  ignoredError,
  ignoredLoading,
  ignoredRows,
  initialize,
  manualReviewActionFailure,
  manualReviewError,
  manualReviewLoading,
  manualReviewRows,
  modelActiveTab,
  modelSelectedAutoFix,
  modelSelectedIgnored,
  modelSelectedManualReview,
  restoreSelected,
  restoreSingle,
  retry,
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
      :class-names="{ content: 'py-0!' }"
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
            class="ml-2 px-0.5! py-0!"
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
            class="ml-2 px-0.5! py-0!"
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
            class="ml-2 px-0.5! py-0!"
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
            :error="autoFixError"
            :action-failure="autoFixActionFailure"
            @retry="retry(DuplicatesTab.AUTO_FIX)"
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
            :error="manualReviewError"
            :action-failure="manualReviewActionFailure"
            @retry="retry(DuplicatesTab.MANUAL_REVIEW)"
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
            :error="ignoredError"
            :action-failure="ignoredActionFailure"
            @retry="retry(DuplicatesTab.IGNORED)"
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

      <CustomizedEventDuplicatesFooter
        :active-tab="modelActiveTab"
        :auto-fix-count="modelSelectedAutoFix.length"
        :manual-review-count="modelSelectedManualReview.length"
        :ignored-count="modelSelectedIgnored.length"
        :fix-loading="fixLoading"
        :ignore-loading="ignoreLoading"
        @fix-selected="fixSelected()"
        @ignore-selected="ignoreSelected()"
        @restore-selected="restoreSelected()"
        @close="closeDialog()"
      />
    </RuiCard>
  </RuiDialog>
</template>
