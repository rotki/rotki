<script setup lang="ts">
import CustomizedEventDuplicatesTable from '@/components/history/events/CustomizedEventDuplicatesTable.vue';
import CardTitle from '@/components/typography/CardTitle.vue';
import { type CustomizedEventDuplicate, useCustomizedEventDuplicates } from '@/composables/history/events/use-customized-event-duplicates';
import { DuplicateHandlingStatus } from '@/composables/history/events/use-history-events-filters';
import { Routes } from '@/router/routes';
import { useConfirmStore } from '@/store/confirm';

const modelValue = defineModel<boolean>({ required: true });

const emit = defineEmits<{
  refresh: [];
}>();

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();
const { show } = useConfirmStore();

const {
  autoFixCount,
  autoFixGroupIds,
  fetchCustomizedEventDuplicates,
  fixDuplicates,
  fixLoading,
  loading,
  manualReviewCount,
  manualReviewGroupIds,
} = useCustomizedEventDuplicates();

const activeTab = ref<number>(0);
const selectedAutoFix = ref<string[]>([]);

async function viewAllEvents(groupIds: string[], status: DuplicateHandlingStatus): Promise<void> {
  const groupIdentifiers = groupIds.join(',');
  closeDialog();
  await router.push({
    path: Routes.HISTORY_EVENTS.toString(),
    query: {
      duplicateHandlingStatus: status,
      groupIdentifiers,
    },
  });
}

async function fixSingleDuplicate(duplicate: CustomizedEventDuplicate): Promise<void> {
  const result = await fixDuplicates([duplicate.groupIdentifier]);
  if (result.success) {
    emit('refresh');
  }
}

function confirmFixSingle(duplicate: CustomizedEventDuplicate): void {
  show({
    message: t('customized_event_duplicates.actions.fix_single_confirm'),
    primaryAction: t('common.actions.confirm'),
    title: t('customized_event_duplicates.actions.fix_single'),
  }, async () => fixSingleDuplicate(duplicate));
}

async function fixSelectedDuplicates(): Promise<void> {
  const result = await fixDuplicates(get(selectedAutoFix));
  if (result.success) {
    set(selectedAutoFix, []);
    emit('refresh');
  }
}

function confirmFixSelected(): void {
  const count = get(selectedAutoFix).length;
  show({
    message: t('customized_event_duplicates.actions.fix_selected_confirm', { count }),
    primaryAction: t('common.actions.confirm'),
    title: t('customized_event_duplicates.actions.fix_selected'),
  }, async () => fixSelectedDuplicates());
}

function closeDialog(): void {
  set(modelValue, false);
}

onBeforeMount(async () => {
  await fetchCustomizedEventDuplicates();
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
            color="secondary"
            size="sm"
            class="ml-2 !px-0.5 !py-0"
          >
            {{ manualReviewCount }}
          </RuiChip>
        </RuiTab>
      </RuiTabs>

      <RuiTabItems
        v-model="activeTab"
        class="my-4"
      >
        <RuiTabItem>
          <div class="flex items-center justify-between mb-4 gap-4">
            <p class="text-body-2 text-rui-text-secondary">
              {{ t('customized_event_duplicates.dialog.auto_fix_description') }}
            </p>
            <RuiButton
              v-if="autoFixCount > 0"
              size="sm"
              variant="outlined"
              :loading="loading"
              @click="viewAllEvents(autoFixGroupIds, DuplicateHandlingStatus.AUTO_FIX)"
            >
              <template #prepend>
                <RuiIcon
                  name="lu-external-link"
                  size="16"
                />
              </template>
              {{ t('customized_event_duplicates.actions.show_all_in_history_events') }}
            </RuiButton>
          </div>

          <CustomizedEventDuplicatesTable
            v-model:selected="selectedAutoFix"
            :group-ids="autoFixGroupIds"
            :empty-description="t('customized_event_duplicates.dialog.no_auto_fix')"
            :fix-loading="fixLoading"
            selectable
            @fix="confirmFixSingle($event)"
          />
        </RuiTabItem>

        <RuiTabItem>
          <div class="flex items-center justify-between mb-4 gap-4">
            <p class="text-body-2 text-rui-text-secondary">
              {{ t('customized_event_duplicates.dialog.manual_review_description') }}
            </p>
            <RuiButton
              v-if="manualReviewCount > 0"
              size="sm"
              variant="outlined"
              :loading="loading"
              @click="viewAllEvents(manualReviewGroupIds, DuplicateHandlingStatus.MANUAL_REVIEW)"
            >
              <template #prepend>
                <RuiIcon
                  name="lu-external-link"
                  size="16"
                />
              </template>
              {{ t('customized_event_duplicates.actions.show_all_in_history_events') }}
            </RuiButton>
          </div>

          <CustomizedEventDuplicatesTable
            :group-ids="manualReviewGroupIds"
            :empty-description="t('customized_event_duplicates.dialog.no_manual_review')"
          />
        </RuiTabItem>
      </RuiTabItems>

      <template #footer>
        <div class="w-full flex justify-between gap-2 pt-2">
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
          </div>
          <RuiButton
            variant="text"
            @click="closeDialog()"
          >
            {{ t('common.actions.close') }}
          </RuiButton>
        </div>
      </template>
    </RuiCard>
  </RuiDialog>
</template>
