<template>
  <settings-option
    #default="{ error, success, update }"
    setting="nftsInNetValue"
    frontend-setting
    @finished="fetchNetValue"
  >
    <v-switch
      v-model="includeNfts"
      class="general-settings__fields__zero-base mb-4 mt-2"
      :label="$t('frontend_settings.label.include_nfts')"
      :hint="$t('frontend_settings.label.include_nfts_hint')"
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
import { setupGeneralStatistics } from '@/composables/statistics';

const includeNfts = ref<boolean>(true);
const { fetchNetValue } = setupGeneralStatistics();
const { frontendSettings } = useSettings();

onMounted(() => {
  const frontendSettingsVal = get(frontendSettings);
  set(includeNfts, frontendSettingsVal.nftsInNetValue);
});
</script>
