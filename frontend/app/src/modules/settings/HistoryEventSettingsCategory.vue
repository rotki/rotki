<script setup lang="ts">
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';
import AutoCreateProfitEventsSetting from '@/modules/settings/general/AutoCreateProfitEventsSetting.vue';
import InternalTxConflictRepullSettings from '@/modules/settings/general/InternalTxConflictRepullSettings.vue';
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
    <SettingsItem setting-key="autoCreateProfitEvents">
      <AutoCreateProfitEventsSetting />
    </SettingsItem>
    <InternalTxConflictRepullSettings />
    <HistoryEventsSkippedExternalEvents />
  </SettingCategory>
</template>
