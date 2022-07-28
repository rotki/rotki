<template>
  <settings-option
    #default="{ error, success, update }"
    setting="includeGasCosts"
    :error-message="$tc('account_settings.messages.gas_costs')"
  >
    <v-switch
      v-model="gasCosts"
      class="accounting-settings__include-gas-costs"
      :label="$tc('accounting_settings.labels.gas_costs')"
      :success-messages="success"
      :error-messages="error"
      color="primary"
      @change="update"
    />
  </settings-option>
</template>

<script setup lang="ts">
import { onMounted, ref } from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import { useSettings } from '@/composables/settings';

const gasCosts = ref(false);
const { accountingSettings } = useSettings();

onMounted(() => {
  const settings = get(accountingSettings);
  set(gasCosts, settings.includeGasCosts);
});
</script>
