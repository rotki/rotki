<template>
  <settings-option
    #default="{ error, success, update }"
    setting="pnlCsvHaveSummary"
    :error-message="$tc('account_settings.messages.have_csv_summary')"
  >
    <v-switch
      v-model="haveCSVSummary"
      class="csv_export_settings__haveCSVSummary"
      :label="
        $tc('account_settings.csv_export_settings.labels.have_csv_summary')
      "
      color="primary"
      :success-messages="success"
      :error-messages="error"
      @change="update"
    />
  </settings-option>
</template>

<script setup lang="ts">
import { onMounted, ref } from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { useSettings } from '@/composables/settings';

const haveCSVSummary = ref(false);
const { accountingSettings } = useSettings();

onMounted(() => {
  const settings = get(accountingSettings);
  set(haveCSVSummary, settings.pnlCsvHaveSummary);
});
</script>
