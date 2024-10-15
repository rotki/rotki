<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <SettingCategory>
    <template #title>
      {{ t('frontend_settings.title') }}
    </template>
    <LanguageSetting />
    <AnimationsEnabledSetting />
    <ScrambleDataSetting />
    <RefreshSetting />
    <QueryPeriodSetting />
    <Explorers />
  </SettingCategory>
</template>
