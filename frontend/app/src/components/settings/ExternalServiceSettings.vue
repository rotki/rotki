<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <SettingCategory>
    <template #title>
      {{ t('general_settings.external_service_setting.title') }}
    </template>
    <div class="flex flex-col gap-4">
      <QueryRetryLimitSetting />
      <ConnectTimeoutSetting />
      <ReadTimeoutSetting />
    </div>
  </SettingCategory>
</template>
