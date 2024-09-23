<script setup lang="ts">
import { CostBasisMethod } from '@/types/user';
import type { ActionDataEntry } from '@/types/action';

const costBasisMethod = ref<CostBasisMethod>(CostBasisMethod.FIFO);
const { costBasisMethod: method } = storeToRefs(useAccountingSettingsStore());

const { t } = useI18n();

function getSuccessMessage(method: ActionDataEntry<CostBasisMethod>) {
  return t('account_settings.messages.cost_basis_method.success', {
    method: method.identifier.toUpperCase(),
  });
}

function getErrorMessage(method: ActionDataEntry<CostBasisMethod>) {
  return t('account_settings.messages.cost_basis_method.error', {
    method: method.identifier.toUpperCase(),
  });
}

function transformMethod(method: ActionDataEntry<CostBasisMethod>) {
  return method.identifier;
}

onMounted(() => {
  set(costBasisMethod, get(method));
});
</script>

<template>
  <SettingsOption
    #default="{ error, success, updateImmediate }"
    setting="costBasisMethod"
    :success-message="getSuccessMessage"
    :error-message="getErrorMessage"
    :transform="transformMethod"
  >
    <CostBasisMethodSettings
      v-model="costBasisMethod"
      class="accounting-settings__cost-basis-method pt-4"
      :success-messages="success ? [success] : []"
      :error-messages="error ? [error] : []"
      :label="t('accounting_settings.trade.labels.cost_basis_method')"
      @update:model-value="updateImmediate($event)"
    />
  </SettingsOption>
</template>
