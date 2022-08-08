<template>
  <settings-option
    #default="{ error, success, update }"
    setting="btcDerivationGapLimit"
    :error-message="$tc('general_settings.validation.btc_derivation_gap.error')"
    :success-message="
      limit =>
        $tc('general_settings.validation.btc_derivation_gap.success', 0, {
          limit
        })
    "
  >
    <v-text-field
      v-model.number="btcDerivationGapLimit"
      outlined
      class="general-settings__fields__btc-derivation-gap"
      :label="$t('general_settings.labels.btc_derivation_gap')"
      type="number"
      :success-messages="success"
      :error-messages="error"
      @change="update($event ? parseInt($event) : $event)"
    />
  </settings-option>
</template>

<script setup lang="ts">
import { onMounted, ref } from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import { useGeneralSettingsStore } from '@/store/settings/general';

const btcDerivationGapLimit = ref<string>('20');

const { btcDerivationGapLimit: limit } = storeToRefs(useGeneralSettingsStore());

onMounted(() => {
  set(btcDerivationGapLimit, get(limit).toString());
});
</script>
