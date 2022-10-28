<template>
  <settings-option
    #default="{ error, success, update }"
    setting="nftsInNetValue"
    frontend-setting
    @finished="fetchNetValue"
  >
    <v-switch
      v-model="includeNfts"
      class="general-settings__fields__zero-base mb-4 mt-2"
      :label="t('frontend_settings.label.include_nfts')"
      :hint="t('frontend_settings.label.include_nfts_hint')"
      persistent-hint
      :success-messages="success"
      :error-messages="error"
      @change="update"
    />
  </settings-option>
</template>

<script setup lang="ts">
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useStatisticsStore } from '@/store/statistics';

const includeNfts = ref<boolean>(true);
const { fetchNetValue } = useStatisticsStore();
const { nftsInNetValue: enabled } = storeToRefs(useFrontendSettingsStore());

onMounted(() => {
  set(includeNfts, get(enabled));
});

const { t } = useI18n();
</script>
