<script setup lang="ts">
import SettingsItem from '@/components/settings/controls/SettingsItem.vue';
import ShowGraphRangeSelectorSetting from '@/components/settings/frontend/ShowGraphRangeSelectorSetting.vue';
import TimeFrameSetting from '@/components/settings/frontend/TimeFrameSetting.vue';
import ZeroBasedGraphSetting from '@/components/settings/frontend/ZeroBasedGraphSetting.vue';
import SettingCategory from '@/components/settings/SettingCategory.vue';

const { t } = useI18n();
</script>

<template>
  <SettingCategory>
    <template #title>
      {{ t('frontend_settings.subtitle.graph_settings') }}
    </template>
    <template #subtitle>
      {{ t('frontend_settings.subtitle.graph_settings_hint') }}
    </template>
    <TimeFrameSetting />
    <SettingsItem>
      <template #title>
        {{ t('frontend_settings.graph_basis.title') }}
      </template>
      <ZeroBasedGraphSetting />
      <ShowGraphRangeSelectorSetting />
    </SettingsItem>
  </SettingCategory>
</template>
