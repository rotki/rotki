<script setup lang="ts">
import CostBasisMethodSettings from '@/components/settings/accounting/CostBasisMethodSettings.vue';
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { CostBasisMethod } from '@/modules/settings/types/user-settings';
import { useAccountingSettingsStore } from '@/modules/settings/use-accounting-settings-store';

const costBasisMethod = ref<CostBasisMethod>(CostBasisMethod.FIFO);
const { costBasisMethod: method } = storeToRefs(useAccountingSettingsStore());

onMounted(() => {
  set(costBasisMethod, get(method));
});

const { t } = useI18n({ useScope: 'global' });

function getSuccessMessage(method: string) {
  return t('account_settings.messages.cost_basis_method.success', {
    method: method.toUpperCase(),
  });
}

function getErrorMessage(method: string) {
  return t('account_settings.messages.cost_basis_method.error', {
    method: method.toUpperCase(),
  });
}
</script>

<template>
  <SettingsOption
    #default="{ error, success, updateImmediate }"
    setting="costBasisMethod"
    :success-message="getSuccessMessage"
    :error-message="getErrorMessage"
  >
    <CostBasisMethodSettings
      v-model="costBasisMethod"
      class="pt-4"
      :success-messages="success ? [success] : []"
      :error-messages="error ? [error] : []"
      :label="t('accounting_settings.trade.labels.cost_basis_method')"
      @update:model-value="updateImmediate($event)"
    />
  </SettingsOption>
</template>
