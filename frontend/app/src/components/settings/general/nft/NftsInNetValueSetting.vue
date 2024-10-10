<script setup lang="ts">
const includeNfts = ref<boolean>(true);
const { fetchNetValue } = useStatisticsStore();
const { nftsInNetValue: enabled } = storeToRefs(useFrontendSettingsStore());

onMounted(() => {
  set(includeNfts, get(enabled));
});

const { t } = useI18n();
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
      class="general-settings__fields__nfts-in-net-value"
      :label="t('general_settings.nft_setting.label.include_nfts')"
      :success-messages="success"
      :error-messages="error"
      @update:model-value="update($event)"
    />
  </SettingsOption>
</template>
