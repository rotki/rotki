<script setup lang="ts">
import HistoryQueryStatusCurrent from '@/components/history/events/HistoryQueryStatusCurrent.vue';

defineProps<{
  finished: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <HistoryQueryStatusCurrent :finished="finished">
    <template #finished>
      {{ t('transactions.events_decoding.decoding.all_done') }}
    </template>

    <template #running>
      {{ t('transactions.events_decoding.decoding.all') }}
    </template>
  </HistoryQueryStatusCurrent>
</template>
