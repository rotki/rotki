<script setup lang="ts">
import SettingsOption from '@/modules/settings/controls/SettingsOption.vue';
import { useFrontendSettingsStore } from '@/modules/settings/use-frontend-settings-store';
import { useStatisticsDataFetching } from '@/modules/statistics/use-statistics-data-fetching';

const includeNfts = ref<boolean>(true);
const { fetchNetValue } = useStatisticsDataFetching();
const { nftsInNetValue: enabled } = storeToRefs(useFrontendSettingsStore());

onMounted(() => {
  set(includeNfts, get(enabled));
});

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingsOption
    #default="{ error, success, update }"
    setting="nftsInNetValue"
    frontend-setting
    @finished="fetchNetValue()"
  >
    <RuiSwitch
      v-model="includeNfts"
      color="primary"
      :label="t('general_settings.nft_setting.label.include_nfts')"
      :success-messages="success"
      :error-messages="error"
      @update:model-value="update($event)"
    />
  </SettingsOption>
</template>
