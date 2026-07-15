<script setup lang="ts">
import { Constraints } from '@/modules/core/common/constraints';
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';
import SettingToggleNumber from '@/modules/settings/controls/SettingToggleNumber.vue';

const minRefreshPeriod = 30;
const maxRefreshPeriod = Constraints.MAX_MINUTES_DELAY;

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingsItem setting-key="refreshPeriod">
    <SettingToggleNumber
      setting="refreshPeriod"
      :enabled-value="minRefreshPeriod"
      :min="minRefreshPeriod"
      :max="maxRefreshPeriod"
      :switch-label="t('frontend_settings.refresh_balance.label')"
      :field-label="t('frontend_settings.refresh_balance.period_label')"
      :validation="{
        empty: t('frontend_settings.refresh_balance.validation.non_empty'),
        invalid: t('frontend_settings.refresh_balance.validation.invalid_period', {
          end: maxRefreshPeriod,
          start: minRefreshPeriod,
        }),
      }"
      :error-message="t('frontend_settings.refresh_balance.validation.error')"
    />
  </SettingsItem>
</template>
