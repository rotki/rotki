<template>
  <settings-option
    #default="{ error, success, update }"
    setting="includeCrypto2crypto"
    :error-message="tc('account_settings.messages.crypto_to_crypto')"
  >
    <v-switch
      v-model="crypto2CryptoTrades"
      class="accounting-settings__crypto2crypto"
      :label="tc('accounting_settings.labels.crypto_to_crypto')"
      color="primary"
      :success-messages="success"
      :error-messages="error"
      @change="update"
    />
  </settings-option>
</template>

<script setup lang="ts">
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { useAccountingSettingsStore } from '@/store/settings/accounting';

const crypto2CryptoTrades = ref(false);
const { includeCrypto2crypto } = storeToRefs(useAccountingSettingsStore());

onMounted(() => {
  set(crypto2CryptoTrades, get(includeCrypto2crypto));
});

const { tc } = useI18n();
</script>
