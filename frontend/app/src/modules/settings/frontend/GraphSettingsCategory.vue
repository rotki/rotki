<script setup lang="ts">
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';
import ShowGraphRangeSelectorSetting from '@/modules/settings/frontend/ShowGraphRangeSelectorSetting.vue';
import TimeFrameSetting from '@/modules/settings/frontend/TimeFrameSetting.vue';
import ZeroBasedGraphSetting from '@/modules/settings/frontend/ZeroBasedGraphSetting.vue';
import { SettingsHighlightIds } from '@/modules/settings/setting-highlight-ids';
import SettingCategory from '@/modules/settings/SettingCategory.vue';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingCategory>
    <template #title>
      {{ t('frontend_settings.subtitle.graph_settings') }}
    </template>
    <template #subtitle>
      {{ t('frontend_settings.subtitle.graph_settings_hint') }}
    </template>
    <TimeFrameSetting :id="SettingsHighlightIds.TIMEFRAME" />
    <SettingsItem :id="SettingsHighlightIds.GRAPH_BASIS">
      <template #title>
        {{ t('frontend_settings.graph_basis.title') }}
      </template>
      <ZeroBasedGraphSetting />
      <ShowGraphRangeSelectorSetting />
    </SettingsItem>
  </SettingCategory>
</template>
