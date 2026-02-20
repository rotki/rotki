<script setup lang="ts">
import AutoCreateProfitEventsSetting from '@/components/settings/general/AutoCreateProfitEventsSetting.vue';
import SettingCategory from '@/components/settings/SettingCategory.vue';
import { SettingsHighlightIds } from '@/composables/settings/types';

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
    <AutoCreateProfitEventsSetting :id="SettingsHighlightIds.AUTO_CREATE_PROFIT_EVENTS" />
    <HistoryEventsSkippedExternalEvents :id="SettingsHighlightIds.SKIPPED_EVENTS" />
  </SettingCategory>
</template>
