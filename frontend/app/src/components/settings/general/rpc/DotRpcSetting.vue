<script lang="ts" setup>
import { Defaults } from '@/data/defaults';

const { t } = useI18n();
const dotRpcEndpoint = ref(Defaults.DOT_RPC_ENDPOINT);

const { dotRpcEndpoint: dotRpc } = storeToRefs(useGeneralSettingsStore());

const dotSuccessMessage = (endpoint: string) => {
  if (endpoint) {
    return t('general_settings.validation.dot_rpc.success_set', {
      endpoint
    });
  }
  return t('general_settings.validation.dot_rpc.success_unset');
};

onBeforeMount(() => {
  set(dotRpcEndpoint, get(dotRpc) || Defaults.DOT_RPC_ENDPOINT);
});
</script>

<template>
  <SettingsOption
    #default="{ error, success, update }"
    setting="dotRpcEndpoint"
    :error-message="t('general_settings.validation.dot_rpc.error')"
    :success-message="dotSuccessMessage"
  >
    <RuiTextField
      v-model="dotRpcEndpoint"
      variant="outlined"
      color="primary"
      class="general-settings__fields__dot-rpc-endpoint"
      :label="t('general_settings.labels.dot_rpc_endpoint')"
      type="text"
      :success-messages="success"
      :error-messages="error"
      clearable
      @paste="update($event.clipboardData.getData('text'))"
      @click:clear="update('')"
      @change="update($event)"
    />
  </SettingsOption>
</template>
