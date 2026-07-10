<script setup lang="ts">
import SettingSwitch from '@/modules/settings/controls/SettingSwitch.vue';
import { useStatisticsDataFetching } from '@/modules/statistics/use-statistics-data-fetching';

const { fetchNetValue } = useStatisticsDataFetching();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingSwitch
    setting="nftsInNetValue"
    :debounce="1500"
    :label="t('general_settings.nft_setting.label.include_nfts')"
    @updated="fetchNetValue()"
  />
</template>
