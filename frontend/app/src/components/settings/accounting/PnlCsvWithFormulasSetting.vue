<template>
  <settings-option
    #default="{ error, success, update }"
    setting="pnlCsvWithFormulas"
    :error-message="tc('account_settings.messages.export_csv_formulas')"
  >
    <v-switch
      v-model="exportCSVFormulas"
      class="csv_export_settings__exportCSVFormulas"
      :label="
        tc('account_settings.csv_export_settings.labels.export_csv_formulas')
      "
      color="primary"
      :success-messages="success"
      :error-messages="error"
      @change="update"
    />
  </settings-option>
</template>

<script setup lang="ts">
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { useAccountingSettingsStore } from '@/store/settings/accounting';

const exportCSVFormulas = ref(false);
const { pnlCsvWithFormulas } = storeToRefs(useAccountingSettingsStore());

onMounted(() => {
  set(exportCSVFormulas, get(pnlCsvWithFormulas));
});

const { tc } = useI18n();
</script>
