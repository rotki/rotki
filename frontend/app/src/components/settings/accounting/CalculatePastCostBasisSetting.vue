<script setup lang="ts">
const calculatePastCostBasis = ref(false);
const { calculatePastCostBasis: enabled } = storeToRefs(
  useAccountingSettingsStore()
);
const { t } = useI18n();
const switchSuccessMessage = (enabled: boolean) =>
  enabled
    ? t('account_settings.messages.cost_basis.enabled')
    : t('account_settings.messages.cost_basis.disabled');

onMounted(() => {
  set(calculatePastCostBasis, get(enabled));
});
</script>

<template>
  <SettingsOption
    #default="{ error, success, update }"
    setting="calculatePastCostBasis"
    :error-message="t('account_settings.messages.cost_basis.error')"
    :success-message="switchSuccessMessage"
  >
    <VSwitch
      v-model="calculatePastCostBasis"
      class="accounting-settings__past-cost-basis"
      :success-messages="success"
      :error-messages="error"
      :label="t('accounting_settings.labels.calculate_past_cost_basis')"
      color="primary"
      @change="update($event)"
    />
  </SettingsOption>
</template>
