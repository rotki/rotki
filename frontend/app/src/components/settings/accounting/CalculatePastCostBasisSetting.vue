<template>
  <settings-option
    #default="{ error, success, update }"
    setting="calculatePastCostBasis"
    :error-message="$tc('account_settings.messages.cost_basis.error')"
    :success-message="
      enabled =>
        enabled
          ? $tc('account_settings.messages.cost_basis.enabled')
          : $tc('account_settings.messages.cost_basis.disabled')
    "
  >
    <v-switch
      v-model="calculatePastCostBasis"
      class="accounting-settings__past-cost-basis"
      :success-messages="success"
      :error-messages="error"
      :label="$tc('accounting_settings.labels.calculate_past_cost_basis')"
      color="primary"
      @change="update"
    />
  </settings-option>
</template>

<script setup lang="ts">
import { onMounted, ref } from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import { useSettings } from '@/composables/settings';

const calculatePastCostBasis = ref(false);
const { accountingSettings } = useSettings();

onMounted(() => {
  const settings = get(accountingSettings);
  set(calculatePastCostBasis, settings.calculatePastCostBasis);
});
</script>
