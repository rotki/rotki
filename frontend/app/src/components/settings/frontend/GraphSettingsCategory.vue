<script setup lang="ts">
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
    <SettingsItem>
      <template #title>
        {{ t('timeframe_settings.default_timeframe') }}
      </template>
      <template #subtitle>
        {{ t('timeframe_settings.default_timeframe_description') }}
      </template>
      <TimeFrameSetting />
    </SettingsItem>
    <SettingsItem>
      <template #title>
        {{ t('frontend_settings.subtitle.graph_basis') }}
      </template>
      <template #subtitle>
        {{ t('frontend_settings.subtitle.show_graph_range_selector') }}
      </template>
      <ZeroBasedGraphSetting />
      <ShowGraphRangeSelectorSetting />
    </SettingsItem>
  </SettingCategory>
</template>
