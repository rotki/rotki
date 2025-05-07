<script setup lang="ts">
import ConnectTimeoutSetting from '@/components/settings/general/external-services/ConnectTimeoutSetting.vue';
import QueryRetryLimitSetting from '@/components/settings/general/external-services/QueryRetryLimitSetting.vue';
import ReadTimeoutSetting from '@/components/settings/general/external-services/ReadTimeoutSetting.vue';
import SettingCategory from '@/components/settings/SettingCategory.vue';

const { t } = useI18n({ useScope: 'global' });
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
