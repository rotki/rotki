<script setup lang="ts">
import { useCustomizedEventDuplicates } from '@/composables/history/events/use-customized-event-duplicates';
import { useUnmatchedAssetMovements } from '@/composables/history/events/use-unmatched-asset-movements';
import { useStatusStore } from '@/store/status';
import { Section, Status } from '@/types/status';

const props = defineProps<{
  loading: boolean;
  mainPage: boolean;
}>();

const emit = defineEmits<{
  'open:match-asset-movements': [];
  'open:customized-event-duplicates': [];
}>();

const { t } = useI18n({ useScope: 'global' });

const { loading, mainPage } = toRefs(props);

const {
  autoMatchLoading,
  refreshUnmatchedAssetMovements,
  unmatchedCount,
} = useUnmatchedAssetMovements();

const {
  fetchCustomizedEventDuplicates,
  totalCount: duplicatesCount,
} = useCustomizedEventDuplicates();

const { getStatus } = useStatusStore();

const showUnmatchedMovements = computed<boolean>(() => !get(autoMatchLoading) && get(unmatchedCount) > 0);
const showDuplicates = computed<boolean>(() => get(duplicatesCount) > 0);

const hasAlerts = logicOr(showUnmatchedMovements, showDuplicates);

const showAlerts = computed<boolean>(() =>
  get(mainPage) && !get(loading) && getStatus(Section.HISTORY) === Status.LOADED && get(hasAlerts),
);

watch(loading, async (isLoading) => {
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
      <li v-if="showDuplicates">
        <div class="flex items-center">
          <span>{{ t('customized_event_duplicates.banner.message', { count: duplicatesCount }) }}</span>
          <RuiButton
            variant="text"
            color="warning"
            size="sm"
            class="ml-2 underline"
            @click="emit('open:customized-event-duplicates')"
          >
            {{ t('customized_event_duplicates.banner.action') }}
          </RuiButton>
        </div>
      </li>
    </ul>
  </RuiAlert>
</template>
