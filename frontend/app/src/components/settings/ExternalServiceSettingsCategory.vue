<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <SettingCategory>
    <template #title>
      {{ t('general_settings.external_service_setting.title') }}
    </template>
    <template #subtitle>
      {{ t('general_settings.external_service_setting.subtitle') }}
    </template>
    <QueryRetryLimitSetting />
    <ConnectTimeoutSetting />
    <ReadTimeoutSetting />
  </SettingCategory>
</template>
