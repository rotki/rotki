<template>
  <card class="mt-8">
    <template #title>
      {{ $tc('general_settings.local_nodes.title') }}
    </template>

    <settings-option
      #default="{ error, success, update }"
      setting="ksmRpcEndpoint"
      :error-message="$tc('general_settings.validation.ksm_rpc.error')"
      :success-message="ksmSuccessMessage"
    >
      <v-text-field
        v-model="ksmRpcEndpoint"
        outlined
        class="general-settings__fields__ksm-rpc-endpoint"
        :label="$tc('general_settings.labels.ksm_rpc_endpoint')"
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
      :error-message="$tc('general_settings.validation.dot_rpc.error')"
      :success-message="dotSuccessMessage"
    >
      <v-text-field
        v-model="dotRpcEndpoint"
        outlined
        class="general-settings__fields__dot-rpc-endpoint"
        :label="$tc('general_settings.labels.dot_rpc_endpoint')"
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

<script lang="ts">
import { defineComponent, onMounted, ref } from '@vue/composition-api';
import { get, set } from '@vueuse/core';
import SettingsOption from '@/components/settings/controls/SettingsOption.vue';
import { useSettings } from '@/composables/settings';
import { Defaults } from '@/data/defaults';
import i18n from '@/i18n';

export default defineComponent({
  name: 'RpcSettings',
  components: { SettingsOption },
  setup() {
    const ksmRpcEndpoint = ref(Defaults.KSM_RPC_ENDPOINT);
    const dotRpcEndpoint = ref(Defaults.DOT_RPC_ENDPOINT);
    const { generalSettings } = useSettings();

    const ksmSuccessMessage = (endpoint: string) => {
      if (endpoint) {
        return i18n.tc('general_settings.validation.ksm_rpc.success_set', 0, {
          endpoint
        });
      }
      return i18n.tc('general_settings.validation.ksm_rpc.success_unset');
    };

    const dotSuccessMessage = (endpoint: string) => {
      if (endpoint) {
        return i18n.tc('general_settings.validation.dot_rpc.success_set', 0, {
          endpoint
        });
      }
      return i18n.tc('general_settings.validation.dot_rpc.success_unset');
    };

    onMounted(() => {
      const settings = get(generalSettings);
      set(ksmRpcEndpoint, settings.ksmRpcEndpoint || Defaults.KSM_RPC_ENDPOINT);
      set(dotRpcEndpoint, settings.dotRpcEndpoint || Defaults.DOT_RPC_ENDPOINT);
    });

    return {
      ksmRpcEndpoint,
      dotRpcEndpoint,
      ksmSuccessMessage,
      dotSuccessMessage
    };
  }
});
</script>
