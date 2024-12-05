<script setup lang="ts">
import { useAccountingSettingsStore } from '@/store/settings/accounting';

const accountForAssetsMovements = ref(false);
const { accountForAssetsMovements: enabled } = storeToRefs(useAccountingSettingsStore());

onMounted(() => {
  set(accountForAssetsMovements, get(enabled));
});

const { t } = useI18n();
</script>

<template>
  <SettingsOption
    #default="{ error, success, update }"
    setting="accountForAssetsMovements"
    :error-message="t('account_settings.messages.account_for_assets_movements')"
  >
    <RuiSwitch
      v-model="accountForAssetsMovements"
      :success-messages="success"
      :error-messages="error"
      :label="t('accounting_settings.trade.labels.account_for_assets_movements')"
      color="primary"
      @update:model-value="update($event)"
    />
  </SettingsOption>
</template>
