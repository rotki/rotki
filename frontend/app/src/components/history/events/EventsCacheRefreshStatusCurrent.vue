<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <HistoryQueryStatusCurrent>
    <template #running>
      {{ t('transactions.cache_refresh.refreshing') }}
    </template>
  </HistoryQueryStatusCurrent>
</template>
