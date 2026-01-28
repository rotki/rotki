<script setup lang="ts">
import AutoCreateProfitEventsSetting from '@/components/settings/general/AutoCreateProfitEventsSetting.vue';
import SettingCategory from '@/components/settings/SettingCategory.vue';

const HistoryEventsSkippedExternalEvents = defineAsyncComponent(
  () => import('@/components/history/events/HistoryEventsSkippedExternalEvents.vue'),
);

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingCategory>
    <template #title>
      {{ t('general_settings.history_event.title') }}
    </template>
    <template #subtitle>
      {{ t('general_settings.history_event.subtitle') }}
    </template>
    <AutoCreateProfitEventsSetting />
    <HistoryEventsSkippedExternalEvents />
  </SettingCategory>
</template>
