<script setup lang="ts">
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { useAccountingSettingsStore } from '@/store/settings/accounting';

const includeFeesInCostBasis = ref(true);
const { includeFeesInCostBasis: enabled } = storeToRefs(useAccountingSettingsStore());

onMounted(() => {
  set(includeFeesInCostBasis, get(enabled));
});

const { t } = useI18n({ useScope: 'global' });

function getSuccessMessage(enabled: boolean) {
  return enabled
    ? t('account_settings.messages.include_fees_in_cost_basis.enabled')
    : t('account_settings.messages.include_fees_in_cost_basis.disabled');
}
</script>

<template>
  <SettingsOption
    #default="{ error, success, update }"
    setting="includeFeesInCostBasis"
    :error-message="t('account_settings.messages.include_fees_in_cost_basis.error')"
    :success-message="getSuccessMessage"
  >
    <RuiSwitch
      v-model="includeFeesInCostBasis"
      data-cy="include-fees-in-cost-basis-switch"
      :success-messages="success"
      :error-messages="error"
      :label="t('accounting_settings.trade.labels.include_fees_in_cost_basis')"
      color="primary"
      @update:model-value="update($event)"
    />
  </SettingsOption>
</template>
