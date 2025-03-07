<script setup lang="ts">
import CommonExternalServiceSetting
  from '@/components/settings/general/external-services/CommonExternalServiceSetting.vue';
import { Defaults } from '@/data/defaults';

const { t } = useI18n();

function minValueMessage(min: number) {
  return t('general_settings.external_service_setting.validation.connect_timeout.invalid_range', { min });
}
</script>

<template>
  <CommonExternalServiceSetting
    :min-value-message="minValueMessage"
    :required-message="t('general_settings.external_service_setting.validation.connect_timeout.non_empty')"
    setting="connectTimeout"
    :label="t('general_settings.external_service_setting.label.connect_timeout')"
    :hint="t('general_settings.external_service_setting.label.connect_timeout_hint')"
    :default-value="Defaults.DEFAULT_CONNECT_TIMEOUT"
  />
</template>
