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
    <VSwitch
      v-model="includeNfts"
      class="general-settings__fields__zero-base mb-4 mt-2"
      :label="t('general_settings.nft_setting.label.include_nfts')"
      :hint="t('general_settings.nft_setting.label.include_nfts_hint')"
      persistent-hint
      :success-messages="success"
      :error-messages="error"
      @change="update($event)"
    />
  </SettingsOption>
</template>
