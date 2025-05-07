<script setup lang="ts">
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { useAccountingSettingsStore } from '@/store/settings/accounting';

const exportCSVFormulas = ref(false);
const { pnlCsvWithFormulas } = storeToRefs(useAccountingSettingsStore());

onMounted(() => {
  set(exportCSVFormulas, get(pnlCsvWithFormulas));
});

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingsOption
    #default="{ error, success, update }"
    setting="pnlCsvWithFormulas"
    :error-message="t('account_settings.messages.export_csv_formulas')"
  >
    <RuiSwitch
      v-model="exportCSVFormulas"
      class="csv_export_settings__exportCSVFormulas"
      :label="t('account_settings.csv_export_settings.labels.export_csv_formulas')"
      color="primary"
      :success-messages="success"
      :error-messages="error"
      @update:model-value="update($event)"
    />
  </SettingsOption>
</template>
