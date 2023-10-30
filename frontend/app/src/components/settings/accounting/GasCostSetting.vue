<script setup lang="ts">
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
    <VSwitch
      v-model="gasCosts"
      class="accounting-settings__include-gas-costs"
      :label="t('accounting_settings.trade.labels.include_gas_costs')"
      :success-messages="success"
      :error-messages="error"
      color="primary"
      @change="update($event)"
    />
  </SettingsOption>
</template>
