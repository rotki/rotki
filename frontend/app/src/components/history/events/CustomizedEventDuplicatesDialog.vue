<script setup lang="ts">
import type { ComputedRef, Ref } from 'vue';
import { Severity } from '@rotki/common';
import CustomizedEventDuplicatesList from '@/components/history/events/CustomizedEventDuplicatesList.vue';
import CardTitle from '@/components/typography/CardTitle.vue';
import { DuplicateHandlingStatus } from '@/composables/history/events/types';
import { type DuplicateRow, useCustomizedEventDuplicates } from '@/composables/history/events/use-customized-event-duplicates';
import { Routes } from '@/router/routes';
import { useNotificationsStore } from '@/store/notifications';
import { logger } from '@/utils/logging';

const modelValue = defineModel<boolean>({ default: false });

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();
const { notify } = useNotificationsStore();

const {
  autoFixCount,
  autoFixGroupIds,
  confirmAndFixDuplicate,
  confirmAndMarkNonDuplicated,
  confirmAndRestore,
  fetchCustomizedEventDuplicates,
  fetchDuplicateEvents,
  fixLoading,
  ignoreLoading,
  ignoredCount,
  ignoredGroupIds,
  manualReviewCount,
  manualReviewGroupIds,
} = useCustomizedEventDuplicates();

const activeTab = ref<number>(0);

const selectedAutoFix = ref<string[]>([]);
const selectedManualReview = ref<string[]>([]);
const selectedIgnored = ref<string[]>([]);

const autoFixRows = ref<DuplicateRow[]>([]);
const manualReviewRows = ref<DuplicateRow[]>([]);
const ignoredRows = ref<DuplicateRow[]>([]);

const autoFixDataLoading = ref<boolean>(false);
const manualReviewDataLoading = ref<boolean>(false);
const ignoredDataLoading = ref<boolean>(false);

async function loadRows(
  groupIds: ComputedRef<string[]>,
  rows: Ref<DuplicateRow[]>,
  loadingRef: Ref<boolean>,
): Promise<void> {
  set(loadingRef, true);
  try {
    const ids = get(groupIds);
    const result = await fetchDuplicateEvents({
      groupIds: ids,
      limit: ids.length || 1,
      offset: 0,
    });
    set(rows, result.data);
  }
  catch (error: any) {
    logger.error('Failed to load duplicate event rows:', error);
    notify({
      display: true,
      message: t('actions.customized_event_duplicates.fetch_events_error.description', { error: error.message }),
      severity: Severity.ERROR,
      title: t('actions.customized_event_duplicates.fetch_events_error.title'),
    });
  }
  finally {
    set(loadingRef, false);
  }
}

async function loadAllRows(): Promise<void> {
  await Promise.all([
    loadRows(autoFixGroupIds, autoFixRows, autoFixDataLoading),
    loadRows(manualReviewGroupIds, manualReviewRows, manualReviewDataLoading),
    loadRows(ignoredGroupIds, ignoredRows, ignoredDataLoading),
  ]);
}

function closeDialog(): void {
  set(modelValue, false);
}

async function showInHistoryEvents(groupIds: string[], status: DuplicateHandlingStatus): Promise<void> {
  if (groupIds.length === 0)
    return;

  closeDialog();
  await router.push({
    path: Routes.HISTORY_EVENTS.toString(),
    query: {
      duplicateHandlingStatus: status,
      groupIdentifiers: groupIds.join(','),
    },
  });
}

function confirmFixSingle(groupId: string): void {
  confirmAndFixDuplicate([groupId], async () => {
    set(selectedAutoFix, get(selectedAutoFix).filter(id => id !== groupId));
    await loadRows(autoFixGroupIds, autoFixRows, autoFixDataLoading);
  });
}

function confirmFixSelected(): void {
  const selected = get(selectedAutoFix);
  if (selected.length === 0)
    return;

  confirmAndFixDuplicate(selected, async () => {
    set(selectedAutoFix, []);
    await loadRows(autoFixGroupIds, autoFixRows, autoFixDataLoading);
  });
}

function confirmIgnoreSingle(groupId: string): void {
  confirmAndMarkNonDuplicated([groupId], async () => {
    set(selectedAutoFix, get(selectedAutoFix).filter(id => id !== groupId));
    set(selectedManualReview, get(selectedManualReview).filter(id => id !== groupId));
    await loadAllRows();
  });
}

function confirmIgnoreSelected(): void {
  const tab = get(activeTab);
  const selected = tab === 0 ? get(selectedAutoFix) : get(selectedManualReview);
  if (selected.length === 0)
    return;

  confirmAndMarkNonDuplicated(selected, async () => {
    if (tab === 0)
      set(selectedAutoFix, []);
    else
      set(selectedManualReview, []);
    await loadAllRows();
  });
}

function confirmRestoreSingle(groupId: string): void {
  confirmAndRestore([groupId], async () => {
    set(selectedIgnored, get(selectedIgnored).filter(id => id !== groupId));
    await loadAllRows();
  });
}

function confirmRestoreSelected(): void {
  const selected = get(selectedIgnored);
  if (selected.length === 0)
    return;

  confirmAndRestore(selected, async () => {
    set(selectedIgnored, []);
    await loadAllRows();
  });
}

onBeforeMount(async () => {
  await fetchCustomizedEventDuplicates();
  await loadAllRows();
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
        v-model="activeTab"
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
        v-model="activeTab"
        class="my-4"
      >
        <RuiTabItem>
          <CustomizedEventDuplicatesList
            v-model:selected="selectedAutoFix"
            :description="t('customized_event_duplicates.dialog.auto_fix_description')"
            :rows="autoFixRows"
            :loading="autoFixDataLoading"
            @show-in-history="showInHistoryEvents(autoFixGroupIds, DuplicateHandlingStatus.AUTO_FIX)"
          >
            <template #actions="{ row }">
              <div class="flex items-center gap-2">
                <RuiButton
                  size="sm"
                  color="primary"
                  :loading="fixLoading"
                  @click="confirmFixSingle(row.groupIdentifier)"
                >
                  <template #prepend>
                    <RuiIcon
                      size="16"
                      name="lu-wand-sparkles"
                    />
                  </template>
                  {{ t('customized_event_duplicates.actions.fix') }}
                </RuiButton>
                <RuiTooltip
                  :open-delay="400"
                  :popper="{ placement: 'top' }"
                >
                  <template #activator>
                    <RuiButton
                      size="sm"
                      variant="outlined"
                      :loading="ignoreLoading"
                      @click="confirmIgnoreSingle(row.groupIdentifier)"
                    >
                      <template #prepend>
                        <RuiIcon
                          size="16"
                          name="lu-eye-off"
                        />
                      </template>
                      {{ t('customized_event_duplicates.actions.mark_non_duplicated') }}
                    </RuiButton>
                  </template>
                  {{ t('customized_event_duplicates.actions.mark_non_duplicated_tooltip') }}
                </RuiTooltip>
              </div>
            </template>
          </CustomizedEventDuplicatesList>
        </RuiTabItem>

        <RuiTabItem>
          <CustomizedEventDuplicatesList
            v-model:selected="selectedManualReview"
            :description="t('customized_event_duplicates.dialog.manual_review_description')"
            :rows="manualReviewRows"
            :loading="manualReviewDataLoading"
            @show-in-history="showInHistoryEvents(manualReviewGroupIds, DuplicateHandlingStatus.MANUAL_REVIEW)"
          >
            <template #actions="{ row }">
              <div class="flex items-center gap-2">
                <RuiTooltip
                  :open-delay="400"
                  :popper="{ placement: 'top' }"
                >
                  <template #activator>
                    <RuiButton
                      size="sm"
                      variant="outlined"
                      :loading="ignoreLoading"
                      @click="confirmIgnoreSingle(row.groupIdentifier)"
                    >
                      <template #prepend>
                        <RuiIcon
                          size="16"
                          name="lu-eye-off"
                        />
                      </template>
                      {{ t('customized_event_duplicates.actions.mark_non_duplicated') }}
                    </RuiButton>
                  </template>
                  {{ t('customized_event_duplicates.actions.mark_non_duplicated_tooltip') }}
                </RuiTooltip>
              </div>
            </template>
          </CustomizedEventDuplicatesList>
        </RuiTabItem>

        <RuiTabItem>
          <CustomizedEventDuplicatesList
            v-model:selected="selectedIgnored"
            :description="t('customized_event_duplicates.dialog.non_duplicated_description')"
            :rows="ignoredRows"
            :loading="ignoredDataLoading"
            @show-in-history="showInHistoryEvents(ignoredGroupIds, DuplicateHandlingStatus.IGNORED)"
          >
            <template #actions="{ row }">
              <div class="flex items-center gap-2">
                <RuiTooltip
                  :open-delay="400"
                  :popper="{ placement: 'top' }"
                >
                  <template #activator>
                    <RuiButton
                      size="sm"
                      color="primary"
                      :loading="ignoreLoading"
                      @click="confirmRestoreSingle(row.groupIdentifier)"
                    >
                      <template #prepend>
                        <RuiIcon
                          size="16"
                          name="lu-rotate-ccw"
                        />
                      </template>
                      {{ t('customized_event_duplicates.actions.restore') }}
                    </RuiButton>
                  </template>
                  {{ t('customized_event_duplicates.actions.restore_tooltip') }}
                </RuiTooltip>
              </div>
            </template>
          </CustomizedEventDuplicatesList>
        </RuiTabItem>
      </RuiTabItems>

      <div class="w-full flex justify-between gap-2 pb-4">
        <div
          v-if="activeTab === 0"
          class="flex gap-2"
        >
          <RuiButton
            variant="outlined"
            color="primary"
            :disabled="selectedAutoFix.length === 0 || fixLoading"
            :loading="fixLoading"
            @click="confirmFixSelected()"
          >
            <template #prepend>
              <RuiIcon
                size="16"
                name="lu-wand-sparkles"
              />
            </template>
            {{ t('customized_event_duplicates.actions.fix_selected') }}
            <RuiChip
              v-if="selectedAutoFix.length > 0"
              size="sm"
              color="primary"
              class="ml-2 !py-0"
            >
              {{ selectedAutoFix.length }}
            </RuiChip>
          </RuiButton>
          <RuiButton
            variant="outlined"
            :disabled="selectedAutoFix.length === 0 || ignoreLoading"
            :loading="ignoreLoading"
            @click="confirmIgnoreSelected()"
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
          v-else-if="activeTab === 1"
          class="flex gap-2"
        >
          <RuiButton
            variant="outlined"
            :disabled="selectedManualReview.length === 0 || ignoreLoading"
            :loading="ignoreLoading"
            @click="confirmIgnoreSelected()"
          >
            <template #prepend>
              <RuiIcon
                size="16"
                name="lu-eye-off"
              />
            </template>
            {{ t('customized_event_duplicates.actions.mark_non_duplicated_selected') }}
            <RuiChip
              v-if="selectedManualReview.length > 0"
              size="sm"
              color="primary"
              class="ml-2 !py-0"
            >
              {{ selectedManualReview.length }}
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
            :disabled="selectedIgnored.length === 0 || ignoreLoading"
            :loading="ignoreLoading"
            @click="confirmRestoreSelected()"
          >
            <template #prepend>
              <RuiIcon
                size="16"
                name="lu-rotate-ccw"
              />
            </template>
            {{ t('customized_event_duplicates.actions.restore_selected') }}
            <RuiChip
              v-if="selectedIgnored.length > 0"
              size="sm"
              color="primary"
              class="ml-2 !py-0"
            >
              {{ selectedIgnored.length }}
            </RuiChip>
          </RuiButton>
        </div>
        <RuiButton
          variant="text"
          @click="closeDialog()"
        >
          {{ t('common.actions.close') }}
        </RuiButton>
      </div>
    </RuiCard>
  </RuiDialog>
</template>
