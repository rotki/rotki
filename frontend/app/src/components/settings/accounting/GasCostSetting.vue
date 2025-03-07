<script setup lang="ts">
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { useAccountingSettingsStore } from '@/store/settings/accounting';

const gasCosts = ref(false);
const { includeGasCosts } = storeToRefs(useAccountingSettingsStore());

onMounted(() => {
  set(gasCosts, get(includeGasCosts));
});

const { t } = useI18n();
</script>

<template>
  <SettingsOption
    #default="{ error, success, update }"
    setting="includeGasCosts"
    :error-message="t('account_settings.messages.gas_costs')"
  >
    <RuiSwitch
      v-model="gasCosts"
      data-cy="include-gas-costs-switch"
      :label="t('accounting_settings.trade.labels.include_gas_costs')"
      :success-messages="success"
      :error-messages="error"
      color="primary"
      @update:model-value="update($event)"
    />
  </SettingsOption>
</template>
