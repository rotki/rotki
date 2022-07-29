<template>
  <settings-option
    #default="{ error, success, update }"
    setting="includeCrypto2crypto"
    :error-message="$tc('account_settings.messages.crypto_to_crypto')"
  >
    <v-switch
      v-model="crypto2CryptoTrades"
      class="accounting-settings__crypto2crypto"
      :label="$tc('accounting_settings.labels.crypto_to_crypto')"
      color="primary"
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

const crypto2CryptoTrades = ref(false);
const { accountingSettings } = useSettings();

onMounted(() => {
  const settings = get(accountingSettings);
  set(crypto2CryptoTrades, settings.includeCrypto2crypto);
});
</script>
