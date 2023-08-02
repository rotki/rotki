<script setup lang="ts">
const { t } = useI18n();

const minValueMessage = (min: number) =>
  t(
    'general_settings.external_service_setting.validation.query_retry_limit.invalid_range',
    { min }
  );
</script>

<template>
  <CommonExternalServiceSetting
    :min-value-message="minValueMessage"
    :required-message="
      t(
        'general_settings.external_service_setting.validation.query_retry_limit.non_empty'
      )
    "
    setting="queryRetryLimit"
    :label="
      t('general_settings.external_service_setting.label.query_retry_limit')
    "
    :hint="
      t(
        'general_settings.external_service_setting.label.query_retry_limit_hint'
      )
    "
  />
</template>
