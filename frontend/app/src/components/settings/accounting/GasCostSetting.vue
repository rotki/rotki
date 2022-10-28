<template>
  <settings-option
    #default="{ error, success, update }"
    setting="includeGasCosts"
    :error-message="tc('account_settings.messages.gas_costs')"
  >
    <v-switch
      v-model="gasCosts"
      class="accounting-settings__include-gas-costs"
      :label="tc('accounting_settings.labels.gas_costs')"
      :success-messages="success"
      :error-messages="error"
      color="primary"
      @change="update"
    />
  </settings-option>
</template>

<script setup lang="ts">
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { useAccountingSettingsStore } from '@/store/settings/accounting';

const gasCosts = ref(false);
const { includeGasCosts } = storeToRefs(useAccountingSettingsStore());

onMounted(() => {
  set(gasCosts, get(includeGasCosts));
});

const { tc } = useI18n();
</script>
