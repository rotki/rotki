<script setup lang="ts">
import { Constraints } from '@/modules/core/common/constraints';
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';
import SettingToggleNumber from '@/modules/settings/controls/SettingToggleNumber.vue';

const maxVersionUpdateCheckFrequency = Constraints.MAX_HOURS_DELAY;

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingsItem>
    <template #title>
      {{ t('general_settings.version_update_check.title') }}
    </template>
    <SettingToggleNumber
      setting="versionUpdateCheckFrequency"
      :enabled-value="24"
      :min="1"
      :max="maxVersionUpdateCheckFrequency"
      :switch-label="t('general_settings.version_update_check.switch')"
      :field-label="t('general_settings.version_update_check.label')"
      :field-hint="t('general_settings.version_update_check.hint')"
      :validation="{
        empty: t('general_settings.version_update_check.validation.non_empty'),
        invalid: t('general_settings.version_update_check.validation.invalid_frequency', {
          end: maxVersionUpdateCheckFrequency,
          start: 1,
        }),
      }"
      :error-message="t('general_settings.version_update_check.validation.error')"
    />
  </SettingsItem>
</template>
