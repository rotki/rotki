<script setup lang="ts">
import AutoCreateProfitEventsSetting from '@/components/settings/general/AutoCreateProfitEventsSetting.vue';
import InternalTxConflictRepullSettings from '@/components/settings/general/InternalTxConflictRepullSettings.vue';
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
    <InternalTxConflictRepullSettings :id="SettingsHighlightIds.INTERNAL_TX_CONFLICT_REPULL" />
    <HistoryEventsSkippedExternalEvents :id="SettingsHighlightIds.SKIPPED_EVENTS" />
  </SettingCategory>
</template>
