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
