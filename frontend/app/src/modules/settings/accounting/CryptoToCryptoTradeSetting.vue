<script setup lang="ts">
import SettingSwitch from '@/modules/settings/controls/SettingSwitch.vue';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingSwitch
    setting="includeCrypto2crypto"
    data-testid="crypto2crypto-switch"
    :debounce="1500"
    :label="t('accounting_settings.trade.labels.include_crypto2crypto')"
    :error-message="t('account_settings.messages.crypto_to_crypto')"
  />
</template>
