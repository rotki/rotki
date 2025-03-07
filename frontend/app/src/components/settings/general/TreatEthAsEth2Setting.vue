<script setup lang="ts">
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { useGeneralSettingsStore } from '@/store/settings/general';

const treatEth2asEth = ref<boolean>(false);
const { treatEth2AsEth: enabled } = storeToRefs(useGeneralSettingsStore());

onMounted(() => {
  set(treatEth2asEth, get(enabled));
});

const { t } = useI18n();
</script>

<template>
  <SettingsOption
    #default="{ error, success, updateImmediate }"
    setting="treatEth2AsEth"
    :error-message="t('general_settings.validation.treat_eth2_as_eth.error')"
  >
    <RuiSwitch
      v-model="treatEth2asEth"
      color="primary"
      :label="t('general_settings.labels.treat_eth2_as_eth')"
      :success-messages="success"
      :error-messages="error"
      @update:model-value="updateImmediate($event)"
    />
  </SettingsOption>
</template>
