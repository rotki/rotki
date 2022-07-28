<template>
  <settings-option
    #default="{ error, success, update }"
    setting="enableEthNames"
    frontend-setting
    :error-message="$tc('frontend_settings.validation.enable_eth_names.error')"
  >
    <v-switch
      v-model="enableEthNames"
      class="general-settings__fields__enable_eth_names mb-4 mt-2"
      :label="$t('frontend_settings.label.enable_eth_names')"
      :success-messages="success"
      :error-messages="error"
      @change="update"
    />
  </settings-option>
</template>

<script setup lang="ts">
import { onMounted, ref } from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import { useSettings } from '@/composables/settings';

const enableEthNames = ref<boolean>(true);
const { frontendSettings } = useSettings();

onMounted(() => {
  const frontendSettingsVal = get(frontendSettings);
  set(enableEthNames, frontendSettingsVal.enableEthNames);
});
</script>
