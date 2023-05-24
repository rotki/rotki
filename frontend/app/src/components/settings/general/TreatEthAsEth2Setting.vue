<script setup lang="ts">
const treatEth2asEth = ref<boolean>(false);
const { treatEth2AsEth: enabled } = storeToRefs(useGeneralSettingsStore());

onMounted(() => {
  set(treatEth2asEth, get(enabled));
});

const { t } = useI18n();
</script>

<template>
  <settings-option
    #default="{ error, success, update }"
    setting="treatEth2AsEth"
    :error-message="t('general_settings.validation.treat_eth2_as_eth.error')"
  >
    <v-switch
      v-model="treatEth2asEth"
      class="general-settings__fields__treat-eth2-as-eth mb-2 mt-0"
      color="primary"
      :label="t('general_settings.labels.treat_eth2_as_eth')"
      :success-messages="success"
      :error-messages="error"
      @change="update($event)"
    />
  </settings-option>
</template>
