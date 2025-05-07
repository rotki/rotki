<script setup lang="ts">
import CommonExternalServiceSetting
  from '@/components/settings/general/external-services/CommonExternalServiceSetting.vue';
import { Defaults } from '@/data/defaults';

const { t } = useI18n({ useScope: 'global' });

function minValueMessage(min: number) {
  return t('general_settings.external_service_setting.validation.query_retry_limit.invalid_range', { min });
}
</script>

<template>
  <CommonExternalServiceSetting
    :min-value-message="minValueMessage"
    :required-message="t('general_settings.external_service_setting.validation.query_retry_limit.non_empty')"
    setting="queryRetryLimit"
    :label="t('general_settings.external_service_setting.label.query_retry_limit')"
    :hint="t('general_settings.external_service_setting.label.query_retry_limit_hint')"
    :default-value="Defaults.DEFAULT_QUERY_RETRY_LIMIT"
  />
</template>
