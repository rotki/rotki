<template>
  <settings-option
    #default="{ error, success, update }"
    setting="graphZeroBased"
    frontend-setting
  >
    <v-switch
      v-model="zeroBased"
      class="general-settings__fields__zero-base mb-4 mt-2"
      :label="$t('frontend_settings.label.zero_based')"
      :hint="$t('frontend_settings.label.zero_based_hint')"
      persistent-hint
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

const zeroBased = ref<boolean>(false);
const { frontendSettings } = useSettings();

onMounted(() => {
  const frontendSettingsVal = get(frontendSettings);
  set(zeroBased, frontendSettingsVal.graphZeroBased);
});
</script>
