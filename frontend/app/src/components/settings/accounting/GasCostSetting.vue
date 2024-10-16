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
    setting="includeGasCosts"
    :error-message="t('account_settings.messages.gas_costs')"
  >
    <template #title>
      {{ t('accounting_settings.trade.titles.gas_costs') }}
    </template>
    <template #default="{ error, success, update }">
      <RuiSwitch
        v-model="gasCosts"
        class="accounting-settings__include-gas-costs"
        :label="t('accounting_settings.trade.labels.include_gas_costs')"
        :success-messages="success"
        :error-messages="error"
        color="primary"
        @update:model-value="update($event)"
      />
    </template>
  </SettingsOption>
</template>
