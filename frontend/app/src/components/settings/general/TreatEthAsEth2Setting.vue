<template>
  <settings-option
    #default="{ error, success, update }"
    setting="treatEth2AsEth"
    :error-message="tc('general_settings.validation.treat_eth2_as_eth.error')"
  >
    <v-switch
      v-model="treatEth2asEth"
      class="general-settings__fields__treat-eth2-as-eth mb-2 mt-0"
      color="primary"
      :label="tc('general_settings.labels.treat_eth2_as_eth')"
      :success-messages="success"
      :error-messages="error"
      @change="update"
    />
  </settings-option>
</template>

<script setup lang="ts">
import { useGeneralSettingsStore } from '@/store/settings/general';

const treatEth2asEth = ref<boolean>(false);
const { treatEth2AsEth: enabled } = storeToRefs(useGeneralSettingsStore());

onMounted(() => {
  set(treatEth2asEth, get(enabled));
});

const { tc } = useI18n();
</script>
