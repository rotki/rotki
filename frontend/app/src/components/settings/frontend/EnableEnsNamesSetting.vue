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
import { get, set } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import { onMounted, ref } from 'vue';
import { useFrontendSettingsStore } from '@/store/settings/frontend';

const enableEthNames = ref<boolean>(true);
const { enableEthNames: enabled } = storeToRefs(useFrontendSettingsStore());

onMounted(() => {
  set(enableEthNames, get(enabled));
});
</script>
