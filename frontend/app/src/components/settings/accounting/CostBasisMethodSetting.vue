<script setup lang="ts">
import CostBasisMethodSettings from '@/components/settings/accounting/CostBasisMethodSettings.vue';
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { useAccountingSettingsStore } from '@/store/settings/accounting';
import { CostBasisMethod } from '@/types/user';

const costBasisMethod = ref<CostBasisMethod>(CostBasisMethod.FIFO);
const { costBasisMethod: method } = storeToRefs(useAccountingSettingsStore());

onMounted(() => {
  set(costBasisMethod, get(method));
});

const { t } = useI18n();

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
