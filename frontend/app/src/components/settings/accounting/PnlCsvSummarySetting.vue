<script setup lang="ts">
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { useAccountingSettingsStore } from '@/store/settings/accounting';

const haveCSVSummary = ref(false);
const { pnlCsvHaveSummary } = storeToRefs(useAccountingSettingsStore());

onMounted(() => {
  set(haveCSVSummary, get(pnlCsvHaveSummary));
});

const { t } = useI18n();
</script>

<template>
  <SettingsOption
    #default="{ error, success, update }"
    setting="pnlCsvHaveSummary"
    :error-message="t('account_settings.messages.have_csv_summary')"
  >
    <RuiSwitch
      v-model="haveCSVSummary"
      class="csv_export_settings__haveCSVSummary"
      :label="t('account_settings.csv_export_settings.labels.have_csv_summary')"
      color="primary"
      :success-messages="success"
      :error-messages="error"
      @update:model-value="update($event)"
    />
  </SettingsOption>
</template>
