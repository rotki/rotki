<script setup lang="ts">
import AutoCreateProfitEventsSetting from '@/modules/settings/general/AutoCreateProfitEventsSetting.vue';
import InternalTxConflictRepullSettings from '@/modules/settings/general/InternalTxConflictRepullSettings.vue';
import { SettingsHighlightIds } from '@/modules/settings/setting-highlight-ids';
import SettingCategory from '@/modules/settings/SettingCategory.vue';

const HistoryEventsSkippedExternalEvents = defineAsyncComponent(
  () => import('@/modules/history/events/HistoryEventsSkippedExternalEvents.vue'),
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
