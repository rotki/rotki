<template>
  <card class="mt-8">
    <template #title>
      {{ tc('general_settings.local_nodes.title') }}
    </template>

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
  </card>
</template>

<script setup lang="ts">
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { Defaults } from '@/data/defaults';
import { useGeneralSettingsStore } from '@/store/settings/general';

const ksmRpcEndpoint = ref(Defaults.KSM_RPC_ENDPOINT);
const dotRpcEndpoint = ref(Defaults.DOT_RPC_ENDPOINT);
const { ksmRpcEndpoint: ksmRpc, dotRpcEndpoint: dotRpc } = storeToRefs(
  useGeneralSettingsStore()
);

const { tc } = useI18n();

const ksmSuccessMessage = (endpoint: string) => {
  if (endpoint) {
    return tc('general_settings.validation.ksm_rpc.success_set', 0, {
      endpoint
    });
  }
  return tc('general_settings.validation.ksm_rpc.success_unset');
};

const dotSuccessMessage = (endpoint: string) => {
  if (endpoint) {
    return tc('general_settings.validation.dot_rpc.success_set', 0, {
      endpoint
    });
  }
  return tc('general_settings.validation.dot_rpc.success_unset');
};

onMounted(() => {
  set(ksmRpcEndpoint, get(ksmRpc) || Defaults.KSM_RPC_ENDPOINT);
  set(dotRpcEndpoint, get(dotRpc) || Defaults.DOT_RPC_ENDPOINT);
});
</script>
