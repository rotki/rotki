<script setup lang="ts">
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';
import QueryPeriodSetting from '@/modules/settings/general/QueryPeriodSetting.vue';
import RefreshSetting from '@/modules/settings/general/RefreshSetting.vue';
import HistoryQueryIndicatorSettings from '@/modules/settings/interface/HistoryQueryIndicatorSettings.vue';
import SettingCategory from '@/modules/settings/SettingCategory.vue';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingCategory>
    <template #title>
      {{ t('frontend_settings.sections.refresh') }}
    </template>
    <RefreshSetting />
    <SettingsItem setting-key="queryPeriod">
      <QueryPeriodSetting />
    </SettingsItem>
    <HistoryQueryIndicatorSettings />
  </SettingCategory>
</template>
