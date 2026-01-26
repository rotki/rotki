<script setup lang="ts">
import { useCustomizedEventDuplicates } from '@/composables/history/events/use-customized-event-duplicates';
import { DuplicateHandlingStatus } from '@/composables/history/events/use-history-events-filters';
import { useUnmatchedAssetMovements } from '@/composables/history/events/use-unmatched-asset-movements';
import { Routes } from '@/router/routes';
import { useStatusStore } from '@/store/status';
import { Section, Status } from '@/types/status';

const show = defineModel<boolean>('show', { required: true });

const props = defineProps<{
  loading: boolean;
  mainPage: boolean;
}>();

const emit = defineEmits<{
  'open:match-asset-movements': [];
}>();

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();
const { getStatus } = useStatusStore();

const { loading, mainPage } = toRefs(props);

const {
  autoMatchLoading,
  refreshUnmatchedAssetMovements,
  unmatchedCount,
} = useUnmatchedAssetMovements();

const {
  autoFixCount,
  autoFixGroupIds,
  fetchCustomizedEventDuplicates,
  manualReviewCount,
  manualReviewGroupIds,
} = useCustomizedEventDuplicates();

const showUnmatchedMovements = computed<boolean>(() => !get(autoMatchLoading) && get(unmatchedCount) > 0);
const showAutoFixDuplicates = computed<boolean>(() => get(autoFixCount) > 0);
const showManualReviewDuplicates = computed<boolean>(() => get(manualReviewCount) > 0);

const hasAlerts = logicOr(showUnmatchedMovements, showAutoFixDuplicates, showManualReviewDuplicates);

const showAlerts = computed<boolean>(() =>
  get(mainPage) && !get(loading) && getStatus(Section.HISTORY) === Status.LOADED && get(hasAlerts) && get(show),
);

function closeAlerts(): void {
  set(show, false);
}

async function viewDuplicates(groupIds: string[], status: DuplicateHandlingStatus): Promise<void> {
  const groupIdentifiers = groupIds.join(',');
  await router.push({
    path: Routes.HISTORY_EVENTS.toString(),
    query: {
      duplicateHandlingStatus: status,
      groupIdentifiers,
    },
  });
}

watchImmediate(loading, async (isLoading) => {
  if (!isLoading && get(mainPage)) {
    await Promise.all([
      refreshUnmatchedAssetMovements(),
      fetchCustomizedEventDuplicates(),
    ]);
  }
});
</script>

<template>
  <RuiAlert
    v-if="showAlerts"
    type="warning"
    class="mb-3"
    closeable
    @close="closeAlerts()"
  >
    <template #title>
      {{ t('transactions.alerts.title') }}
    </template>
    <ul class="list-disc pl-4">
      <li v-if="showUnmatchedMovements">
        <div class="flex items-center">
          <span>{{ t('asset_movement_matching.banner.message', { count: unmatchedCount }) }}</span>
          <RuiButton
            variant="text"
            color="warning"
            size="sm"
            class="ml-2 underline"
            @click="emit('open:match-asset-movements')"
          >
            {{ t('asset_movement_matching.banner.action') }}
          </RuiButton>
        </div>
      </li>
      <li v-if="showAutoFixDuplicates">
        <div class="flex items-center">
          <span>{{ t('customized_event_duplicates.banner.auto_fix_message', { count: autoFixCount }) }}</span>
          <RuiButton
            variant="text"
            color="warning"
            size="sm"
            class="ml-2 underline"
            @click="viewDuplicates(autoFixGroupIds, DuplicateHandlingStatus.AUTO_FIX)"
          >
            {{ t('customized_event_duplicates.banner.view_action') }}
          </RuiButton>
        </div>
      </li>
      <li v-if="showManualReviewDuplicates">
        <div class="flex items-center">
          <span>{{ t('customized_event_duplicates.banner.manual_review_message', { count: manualReviewCount }) }}</span>
          <RuiButton
            variant="text"
            color="warning"
            size="sm"
            class="ml-2 underline"
            @click="viewDuplicates(manualReviewGroupIds, DuplicateHandlingStatus.MANUAL_REVIEW)"
          >
            {{ t('customized_event_duplicates.banner.view_action') }}
          </RuiButton>
        </div>
      </li>
    </ul>
  </RuiAlert>
</template>
