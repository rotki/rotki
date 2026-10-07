<script setup lang="ts">
import { Constraints } from '@/modules/core/common/constraints';
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';
import SettingToggleNumber from '@/modules/settings/controls/SettingToggleNumber.vue';

const DEFAULT_PERIOD_MINUTES = 15;

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingsItem setting-key="autoLogoutPeriod">
    <template #subtitle>
      {{ t('auto_logout_setting.subtitle') }}
    </template>
    <SettingToggleNumber
      setting="autoLogoutPeriod"
      :enabled-value="DEFAULT_PERIOD_MINUTES"
      :min="Constraints.AUTO_LOGOUT_MIN_MINUTES"
      :max="Constraints.AUTO_LOGOUT_MAX_MINUTES"
      :switch-label="t('auto_logout_setting.label')"
      :field-label="t('auto_logout_setting.period_label')"
      :field-hint="t('auto_logout_setting.hint')"
      switch-test-id="auto-logout-toggle"
      field-test-id="auto-logout-period-input"
      :validation="{
        empty: t('auto_logout_setting.validation.non_empty'),
        invalid: t('auto_logout_setting.validation.invalid_period', {
          end: Constraints.AUTO_LOGOUT_MAX_MINUTES,
          start: Constraints.AUTO_LOGOUT_MIN_MINUTES,
        }),
      }"
      :error-message="t('auto_logout_setting.validation.error')"
    />
  </SettingsItem>
</template>
