<script setup lang="ts">
const btcDerivationGapLimit = ref<string>('20');

const { btcDerivationGapLimit: limit } = storeToRefs(useGeneralSettingsStore());
const { t } = useI18n();

function successMessage(limit: string) {
  return t('general_settings.validation.btc_derivation_gap.success', {
    limit,
  });
}

onMounted(() => {
  set(btcDerivationGapLimit, get(limit).toString());
});
</script>

<template>
  <SettingsOption
    #default="{ error, success, update }"
    setting="btcDerivationGapLimit"
    :error-message="t('general_settings.validation.btc_derivation_gap.error')"
    :success-message="successMessage"
  >
    <RuiTextField
      v-model.number="btcDerivationGapLimit"
      variant="outlined"
      color="primary"
      class="general-settings__fields__btc-derivation-gap"
      :label="t('general_settings.labels.btc_derivation_gap')"
      type="number"
      :success-messages="success"
      :error-messages="error"
      @update:model-value="update($event ? parseInt($event) : $event)"
    />
  </SettingsOption>
</template>
