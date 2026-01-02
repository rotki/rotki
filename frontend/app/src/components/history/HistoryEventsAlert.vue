<script setup lang="ts">
import { useStatusUpdater } from '@/composables/status';
import { Routes } from '@/router/routes';
import { Section } from '@/types/status';

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
        <RouterLink :to="Routes.HISTORY">
          <span class="underline">{{ t('transactions.title') }}</span>
        </RouterLink>
      </template>
    </i18n-t>
  </RuiAlert>
</template>
