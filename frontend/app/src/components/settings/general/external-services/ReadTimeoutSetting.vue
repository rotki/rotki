<script setup lang="ts">
const { t } = useI18n();

const minValueMessage = (min: number) =>
  t(
    'general_settings.external_service_setting.validation.read_timeout.invalid_range',
    { min }
  );
</script>

<template>
  <CommonExternalServiceSetting
    :min-value-message="minValueMessage"
    :required-message="
      t(
        'general_settings.external_service_setting.validation.read_timeout.non_empty'
      )
    "
    setting="readTimeout"
    :label="t('general_settings.external_service_setting.label.read_timeout')"
    :hint="
      t('general_settings.external_service_setting.label.read_timeout_hint')
    "
  />
</template>
