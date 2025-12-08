<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router';
import { Routes } from '@/router/routes';

const props = defineProps<{
  service: 'etherscan' | 'helius' | 'beaconchain' | 'consensusRpc';
}>();

const { t } = useI18n({ useScope: 'global' });

const message = computed<string>(() => {
  if (props.service === 'etherscan')
    return t('external_services.etherscan.api_key_message');

  if (props.service === 'consensusRpc')
    return t('general_settings.rpc_node_setting.consensus_rpc.api_key_message');

  if (props.service === 'beaconchain')
    return t('external_services.beaconchain.api_key_message');

  return t('external_services.helius.api_key_message');
});

const [DefineOptionBlock, ReuseOptionBlock] = createReusableTemplate<{
  title?: string;
  description?: string;
  buttonText: string;
  route: RouteLocationRaw;
}>();
</script>

<template>
  <DefineOptionBlock #default="{ title, description, buttonText, route }">
    <div v-if="title && description">
      <div class="font-bold gap-2 flex items-center">
        <div>{{ title }}</div>
        <RouterLink :to="route">
          <RuiButton
            color="primary"
            variant="text"
            size="sm"
            class="inline -my-1 ml-auto [&>span]:underline"
          >
            {{ buttonText }}
          </RuiButton>
        </RouterLink>
      </div>
      <div class="text-xs">
        {{ description }}
      </div>
    </div>
    <RouterLink
      v-else
      :to="route"
    >
      <RuiButton
        color="primary"
        variant="text"
        size="sm"
        class="inline -my-1 ml-auto [&>span]:underline"
      >
        {{ buttonText }}
      </RuiButton>
    </RouterLink>
  </DefineOptionBlock>

  <div>
    {{ message }}
    <div
      v-if="service === 'consensusRpc'"
      class="flex flex-col gap-2 mt-2"
    >
      <ReuseOptionBlock
        :title="t('general_settings.rpc_node_setting.consensus_rpc.beaconchain_only.title')"
        :description="t('general_settings.rpc_node_setting.consensus_rpc.beaconchain_only.description')"
        :button-text="t('notification_messages.missing_api_key.action')"
        :route="{
          path: Routes.API_KEYS_EXTERNAL_SERVICES.toString(),
          query: { service: 'beaconchain' },
        }"
      />
      <ReuseOptionBlock
        :title="t('general_settings.rpc_node_setting.consensus_rpc.consensus_rpc_only.title')"
        :description="t('general_settings.rpc_node_setting.consensus_rpc.consensus_rpc_only.description')"
        :button-text="t('general_settings.rpc_node_setting.consensus_rpc.consensus_rpc_only.input_rpc')"
        :route="{
          path: Routes.SETTINGS_RPC.toString(),
          query: { tab: 'eth_consensus_layer' },
        }"
      />
    </div>
    <template v-else>
      <ReuseOptionBlock
        :button-text="t('notification_messages.missing_api_key.action')"
        :route="{
          path: Routes.API_KEYS_EXTERNAL_SERVICES.toString(),
          query: { service },
        }"
      />
      <ReuseOptionBlock
        v-if="service === 'etherscan'"
        :button-text="t('external_services.etherscan.change_indexer.action')"
        :route="Routes.SETTINGS_EVM.toString()"
      />
    </template>
  </div>
</template>
