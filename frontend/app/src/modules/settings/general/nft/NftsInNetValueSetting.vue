<script setup lang="ts">
import SettingsOption from '@/modules/settings/controls/SettingsOption.vue';
import { useSetting } from '@/modules/settings/use-setting';
import { useStatisticsDataFetching } from '@/modules/statistics/use-statistics-data-fetching';

const includeNfts = ref<boolean>(true);
const { fetchNetValue } = useStatisticsDataFetching();
const enabled = useSetting('nftsInNetValue');

onMounted(() => {
  set(includeNfts, get(enabled));
});

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingsOption
    #default="{ error, success, update }"
    setting="nftsInNetValue"
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
