<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <SettingCategory>
    <template #title>
      {{ t('database_settings.skipped_events.title') }}
    </template>
    <template #subtitle>
      {{ t('database_settings.skipped_events.subtitle') }}
    </template>
    <HistoryEventsSkippedExternalEvents />
  </SettingCategory>
</template>
