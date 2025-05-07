<script setup lang="ts">
import HistoryQueryStatusCurrent from '@/components/history/events/HistoryQueryStatusCurrent.vue';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <HistoryQueryStatusCurrent>
    <template #running>
      {{ t('transactions.cache_refresh.refreshing') }}
    </template>
  </HistoryQueryStatusCurrent>
</template>
