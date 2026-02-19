<script setup lang="ts">
import { DIALOG_TYPES, type DialogShowOptions } from '@/components/history/events/dialog-types';
import { useCustomizedEventDuplicates } from '@/composables/history/events/use-customized-event-duplicates';
import { useUnmatchedAssetMovements } from '@/composables/history/events/use-unmatched-asset-movements';

const showAlerts = defineModel<boolean>('showAlerts', { default: false });

const emit = defineEmits<{
  'show:dialog': [options: DialogShowOptions];
}>();

const { t } = useI18n({ useScope: 'global' });

const { autoMatchLoading, unmatchedCount } = useUnmatchedAssetMovements();
const { actionableCount: duplicatesCount } = useCustomizedEventDuplicates();

const totalIssuesCount = computed<number>(() => get(unmatchedCount) + get(duplicatesCount));
const hasIssues = computed<boolean>(() => !get(autoMatchLoading) && get(totalIssuesCount) > 0);
const hasOnlyUnmatchedMovements = computed<boolean>(() => get(unmatchedCount) > 0 && get(duplicatesCount) === 0);
const hasOnlyDuplicates = computed<boolean>(() => get(unmatchedCount) === 0 && get(duplicatesCount) > 0);

function toggleAlerts(): void {
  if (get(hasOnlyUnmatchedMovements)) {
    emit('show:dialog', { type: DIALOG_TYPES.MATCH_ASSET_MOVEMENTS });
  }
  else if (get(hasOnlyDuplicates)) {
    emit('show:dialog', { type: DIALOG_TYPES.CUSTOMIZED_EVENT_DUPLICATES });
  }
  else {
    set(showAlerts, !get(showAlerts));
  }
}

watch(hasIssues, (value) => {
  if (!value)
    set(showAlerts, false);
});
</script>

<template>
  <RuiBadge
    v-if="hasIssues"
    :text="totalIssuesCount.toString()"
    color="warning"
    placement="top"
    offset-y="4"
    offset-x="-4"
  >
    <RuiButton
      variant="outlined"
      color="warning"
      class="h-9 [&>span]:!hidden lg:[&>span]:!inline"
      @click="toggleAlerts()"
    >
      <template #prepend>
        <RuiIcon
          name="lu-triangle-alert"
          size="18"
        />
      </template>
      {{ t('transactions.alerts.button') }}
      <template #append>
        <RuiIcon
          name="lu-chevron-down"
          size="16"
          class="transition-transform duration-200"
          :class="{ 'rotate-180': showAlerts }"
        />
      </template>
    </RuiButton>
  </RuiBadge>
</template>
