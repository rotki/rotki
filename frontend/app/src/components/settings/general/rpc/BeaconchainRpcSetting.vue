<script lang="ts" setup>
import { Defaults } from '@/data/defaults';
import { useGeneralSettingsStore } from '@/store/settings/general';
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';

const { t } = useI18n();
const beaconRpcEndpoint = ref(Defaults.BEACON_RPC_ENDPOINT);

const { beaconRpcEndpoint: beaconRpc } = storeToRefs(useGeneralSettingsStore());

function beaconSuccessMessage(endpoint: string) {
  if (endpoint) {
    return t('general_settings.validation.beacon_rpc.success_set', {
      endpoint,
    });
  }
  return t('general_settings.validation.beacon_rpc.success_unset');
}

onBeforeMount(() => {
  set(beaconRpcEndpoint, get(beaconRpc) || Defaults.BEACON_RPC_ENDPOINT);
});
</script>

<template>
  <SettingsOption
    #default="{ error, success, update }"
    setting="beaconRpcEndpoint"
    :error-message="t('general_settings.validation.beacon_rpc.error')"
    :success-message="beaconSuccessMessage"
  >
    <RuiTextField
      v-model="beaconRpcEndpoint"
      variant="outlined"
      color="primary"
      class="pt-2"
      :label="t('general_settings.labels.beacon_rpc_endpoint')"
      type="text"
      :success-messages="success"
      :error-messages="error"
      clearable
      @paste="update($event.clipboardData.getData('text'))"
      @click:clear="update('')"
      @update:model-value="update($event)"
    />
  </SettingsOption>
</template>
