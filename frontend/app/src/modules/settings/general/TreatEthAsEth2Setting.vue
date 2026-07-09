<script setup lang="ts">
import SettingSwitch from '@/modules/settings/controls/SettingSwitch.vue';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingSwitch
    setting="treatEth2AsEth"
    :label="t('general_settings.labels.treat_eth2_as_eth')"
    :error-message="t('general_settings.validation.treat_eth2_as_eth.error')"
  />
</template>
