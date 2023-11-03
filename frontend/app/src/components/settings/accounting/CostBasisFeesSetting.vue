<script setup lang="ts">
const includeFeesInCostBasis = ref(true);
const { includeFeesInCostBasis: enabled } = storeToRefs(
  useAccountingSettingsStore()
);

onMounted(() => {
  set(includeFeesInCostBasis, get(enabled));
});

const { t } = useI18n();

const getSuccessMessage = (enabled: boolean) =>
  enabled
    ? t('account_settings.messages.include_fees_in_cost_basis.enabled')
    : t('account_settings.messages.include_fees_in_cost_basis.disabled');
</script>

<template>
  <SettingsOption
    #default="{ error, success, update }"
    setting="includeFeesInCostBasis"
    :error-message="
      t('account_settings.messages.include_fees_in_cost_basis.error')
    "
    :success-message="getSuccessMessage"
  >
    <VSwitch
      v-model="includeFeesInCostBasis"
      class="accounting-settings__include-fees-in-cost-basis"
      :success-messages="success"
      :error-messages="error"
      :label="t('accounting_settings.trade.labels.include_fees_in_cost_basis')"
      color="primary"
      @change="update($event)"
    />
  </SettingsOption>
</template>
