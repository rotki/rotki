<template>
  <settings-option
    #default="{ error, success, update }"
    setting="pnlCsvHaveSummary"
    :error-message="tc('account_settings.messages.have_csv_summary')"
  >
    <v-switch
      v-model="haveCSVSummary"
      class="csv_export_settings__haveCSVSummary"
      :label="
        tc('account_settings.csv_export_settings.labels.have_csv_summary')
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

const haveCSVSummary = ref(false);
const { pnlCsvHaveSummary } = storeToRefs(useAccountingSettingsStore());

onMounted(() => {
  set(haveCSVSummary, get(pnlCsvHaveSummary));
});

const { tc } = useI18n();
</script>
