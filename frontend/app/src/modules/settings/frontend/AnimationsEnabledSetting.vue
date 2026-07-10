<script setup lang="ts">
import SettingSwitch from '@/modules/settings/controls/SettingSwitch.vue';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingSwitch
    setting="animationsEnabled"
    inverted
    data-testid="animations-enabled"
    :label="t('frontend_settings.animations.animations_note')"
    :error-message="t('frontend_settings.animations.validation.error')"
  />
</template>
