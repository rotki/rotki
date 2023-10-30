<script setup lang="ts">
const crypto2CryptoTrades = ref(false);
const { includeCrypto2crypto } = storeToRefs(useAccountingSettingsStore());

onMounted(() => {
  set(crypto2CryptoTrades, get(includeCrypto2crypto));
});

const { t } = useI18n();
</script>

<template>
  <SettingsOption
    #default="{ error, success, update }"
    setting="includeCrypto2crypto"
    :error-message="t('account_settings.messages.crypto_to_crypto')"
  >
    <VSwitch
      v-model="crypto2CryptoTrades"
      class="accounting-settings__crypto2crypto"
      :label="t('accounting_settings.trade.labels.include_crypto2crypto')"
      color="primary"
      :success-messages="success"
      :error-messages="error"
      @change="update($event)"
    />
  </SettingsOption>
</template>
