<template>
  <settings-option
    #default="{ error, success, update }"
    setting="costBasisMethod"
    :success-message="
      method =>
        tc('account_settings.messages.cost_basis_method.success', 0, {
          method: method.toUpperCase()
        })
    "
    :error-message="
      method =>
        tc('account_settings.messages.cost_basis_method.error', 0, {
          method: method.toUpperCase()
        })
    "
  >
    <cost-basis-method-settings
      v-model="costBasisMethod"
      class="accounting-settings__cost-basis-method pt-4"
      :success-messages="success"
      :error-messages="error"
      :label="tc('accounting_settings.labels.cost_basis_method')"
      color="primary"
      @change="update"
    />
  </settings-option>
</template>

<script setup lang="ts">
import CostBasisMethodSettings from '@/components/settings/accounting/CostBasisMethodSettings.vue';
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { useAccountingSettingsStore } from '@/store/settings/accounting';
import { CostBasisMethod } from '@/types/user';

const costBasisMethod = ref<CostBasisMethod>(CostBasisMethod.Fifo);
const { costBasisMethod: method } = storeToRefs(useAccountingSettingsStore());

onMounted(() => {
  set(costBasisMethod, get(method));
});

const { tc } = useI18n();
</script>
