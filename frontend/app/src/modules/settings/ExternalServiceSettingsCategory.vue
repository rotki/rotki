<script setup lang="ts">
import ConnectTimeoutSetting from '@/modules/settings/general/external-services/ConnectTimeoutSetting.vue';
import QueryRetryLimitSetting from '@/modules/settings/general/external-services/QueryRetryLimitSetting.vue';
import ReadTimeoutSetting from '@/modules/settings/general/external-services/ReadTimeoutSetting.vue';
import SuppressMissingKeyServicesSetting
  from '@/modules/settings/general/external-services/SuppressMissingKeyServicesSetting.vue';
import { SettingsHighlightIds } from '@/modules/settings/setting-highlight-ids';
import SettingCategory from '@/modules/settings/SettingCategory.vue';

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
    <QueryRetryLimitSetting :id="SettingsHighlightIds.QUERY_RETRY_LIMIT" />
    <ConnectTimeoutSetting :id="SettingsHighlightIds.CONNECT_TIMEOUT" />
    <ReadTimeoutSetting :id="SettingsHighlightIds.READ_TIMEOUT" />
    <SuppressMissingKeyServicesSetting />
  </SettingCategory>
</template>
