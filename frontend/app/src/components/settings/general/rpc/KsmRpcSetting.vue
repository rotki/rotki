<script lang="ts" setup>
import { Defaults } from '@/data/defaults';

const { tc } = useI18n();
const ksmRpcEndpoint = ref(Defaults.KSM_RPC_ENDPOINT);

const { ksmRpcEndpoint: ksmRpc } = storeToRefs(useGeneralSettingsStore());

const ksmSuccessMessage = (endpoint: string) => {
  if (endpoint) {
    return tc('general_settings.validation.ksm_rpc.success_set', 0, {
      endpoint
    });
  }
  return tc('general_settings.validation.ksm_rpc.success_unset');
};

onBeforeMount(() => {
  set(ksmRpcEndpoint, get(ksmRpc) || Defaults.KSM_RPC_ENDPOINT);
});
</script>

<template>
  <settings-option
    #default="{ error, success, update }"
    setting="ksmRpcEndpoint"
    :error-message="tc('general_settings.validation.ksm_rpc.error')"
    :success-message="ksmSuccessMessage"
  >
    <v-text-field
      v-model="ksmRpcEndpoint"
      outlined
      class="general-settings__fields__ksm-rpc-endpoint"
      :label="tc('general_settings.labels.ksm_rpc_endpoint')"
      type="text"
      :success-messages="success"
      :error-messages="error"
      clearable
      @paste="update($event.clipboardData.getData('text'))"
      @click:clear="update('')"
      @change="update($event)"
    />
  </settings-option>
</template>
