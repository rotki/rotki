<script setup lang="ts">
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { useAccountingSettingsStore } from '@/store/settings/accounting';

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
    <RuiSwitch
      v-model="crypto2CryptoTrades"
      data-cy="crypto2crypto-switch"
      :label="t('accounting_settings.trade.labels.include_crypto2crypto')"
      color="primary"
      :success-messages="success"
      :error-messages="error"
      @update:model-value="update($event)"
    />
  </SettingsOption>
</template>
