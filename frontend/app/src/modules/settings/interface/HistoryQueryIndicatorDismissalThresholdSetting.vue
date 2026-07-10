<script setup lang="ts">
import { Constraints } from '@/modules/core/common/constraints';
import SettingNumber from '@/modules/settings/controls/SettingNumber.vue';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingNumber
    setting="evmQueryIndicatorDismissalThreshold"
    :label="t('frontend_settings.history_query_indicator.dismissal_threshold.label')"
    :min="1"
    :max="Constraints.MAX_HOURS_DELAY"
    :error-message="t('frontend_settings.history_query_indicator.dismissal_threshold.validation.error')"
  />
</template>
