<script setup lang="ts">
import CommonExternalServiceSetting
  from '@/components/settings/general/external-services/CommonExternalServiceSetting.vue';
import { Defaults } from '@/data/defaults';

const { t } = useI18n({ useScope: 'global' });

function minValueMessage(min: number) {
  return t('general_settings.external_service_setting.validation.read_timeout.invalid_range', { min });
}
</script>

<template>
  <CommonExternalServiceSetting
    :min-value-message="minValueMessage"
    :required-message="t('general_settings.external_service_setting.validation.read_timeout.non_empty')"
    setting="readTimeout"
    :label="t('general_settings.external_service_setting.label.read_timeout')"
    :hint="t('general_settings.external_service_setting.label.read_timeout_hint')"
    :default-value="Defaults.DEFAULT_READ_TIMEOUT"
  />
</template>
