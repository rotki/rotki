<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <SettingCategory>
    <template #title>
      {{ t('general_settings.external_service_setting.title') }}
    </template>
    <div>
      <QueryRetryLimitSetting />
      <ConnectTimeoutSetting />
      <ReadTimeoutSetting />
    </div>
  </SettingCategory>
</template>
