<script lang="ts" setup>
import { Defaults } from '@/data/defaults';

const { tc } = useI18n();
const dotRpcEndpoint = ref(Defaults.DOT_RPC_ENDPOINT);

const { dotRpcEndpoint: dotRpc } = storeToRefs(useGeneralSettingsStore());

const dotSuccessMessage = (endpoint: string) => {
  if (endpoint) {
    return tc('general_settings.validation.dot_rpc.success_set', 0, {
      endpoint
    });
  }
  return tc('general_settings.validation.dot_rpc.success_unset');
};

onBeforeMount(() => {
  set(dotRpcEndpoint, get(dotRpc) || Defaults.DOT_RPC_ENDPOINT);
});
</script>

<template>
  <settings-option
    #default="{ error, success, update }"
    setting="dotRpcEndpoint"
    :error-message="tc('general_settings.validation.dot_rpc.error')"
    :success-message="dotSuccessMessage"
  >
    <v-text-field
      v-model="dotRpcEndpoint"
      outlined
      class="general-settings__fields__dot-rpc-endpoint"
      :label="tc('general_settings.labels.dot_rpc_endpoint')"
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
