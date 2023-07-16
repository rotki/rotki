<script setup lang="ts">
const exportCSVFormulas = ref(false);
const { pnlCsvWithFormulas } = storeToRefs(useAccountingSettingsStore());

onMounted(() => {
  set(exportCSVFormulas, get(pnlCsvWithFormulas));
});

const { t } = useI18n();
</script>

<template>
  <SettingsOption
    #default="{ error, success, update }"
    setting="pnlCsvWithFormulas"
    :error-message="t('account_settings.messages.export_csv_formulas')"
  >
    <VSwitch
      v-model="exportCSVFormulas"
      class="csv_export_settings__exportCSVFormulas"
      :label="
        t('account_settings.csv_export_settings.labels.export_csv_formulas')
      "
      color="primary"
      :success-messages="success"
      :error-messages="error"
      @change="update($event)"
    />
  </SettingsOption>
</template>
