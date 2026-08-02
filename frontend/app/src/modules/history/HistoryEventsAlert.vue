<script setup lang="ts">
import { ActivityKind } from '@/modules/task-center/core/types';
import { useTaskCenter } from '@/modules/task-center/use-task-center';

const { t } = useI18n({ useScope: 'global' });
const { useWorkStatus } = useTaskCenter();

// Nudge until a history refresh has completed at least once.
const historySyncStatus = useWorkStatus(ActivityKind.HISTORY_SYNC);
const showAlert = computed<boolean>(() => !get(historySyncStatus).everCompleted);
</script>

<template>
  <RuiAlert
    v-if="showAlert"
    type="info"
  >
    <i18n-t
      scope="global"
      keypath="history_events_alert.nudge"
    >
      <template #link>
        <RouterLink :to="{ name: '/history/events/' }">
          <span class="underline">{{ t('transactions.title') }}</span>
        </RouterLink>
      </template>
    </i18n-t>
  </RuiAlert>
</template>
