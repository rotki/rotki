<script setup lang="ts">
import { Section } from '@/modules/core/common/status';
import { useStatusUpdater } from '@/modules/shell/sync-progress/use-status-updater';

const { t } = useI18n({ useScope: 'global' });
const { isFirstLoad } = useStatusUpdater(Section.HISTORY);

const showAlert = computed<boolean>(() => isFirstLoad());
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
