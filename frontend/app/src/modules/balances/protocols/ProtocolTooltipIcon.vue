<script lang="ts" setup>
import { Blockchain, type ProtocolBalance, toSentenceCase, transformCase } from '@rotki/common';
import { AssetAmountDisplay, FiatDisplay, ValueDisplay } from '@/modules/amount-display/components';
import ProtocolIcon from '@/modules/balances/protocols/ProtocolIcon.vue';
import { useProtocolData } from '@/modules/balances/protocols/use-protocol-data';
import { useProxyProtocol } from '@/modules/balances/protocols/use-proxy-protocol';
import HashLink from '@/modules/common/links/HashLink.vue';
import { useFrontendSettingsStore } from '@/modules/settings/use-frontend-settings-store';

const { protocolBalance, asset, loading } = defineProps<{
  protocolBalance: ProtocolBalance;
  asset?: string;
  loading?: boolean;
}>();

const { shouldShowAmount } = storeToRefs(useFrontendSettingsStore());

const { t } = useI18n({ useScope: 'global' });
const { isProxy, parsedProtocol, proxyAddress } = useProxyProtocol(() => protocolBalance.protocol);
const { protocolData } = useProtocolData(parsedProtocol);

const transformedProtocol = computed<string>(() => {
  const value = protocolBalance.protocol;
  if (get(isProxy)) {
    const parts = value.split(':');
    // Only transform the protocol part, keep the address intact
    return `proxy:${transformCase(parts[1] ?? '')}:${parts[2] ?? ''}`;
  }
  return transformCase(value);
});

const name = computed<string>(() => {
  const data = get(protocolData);
  const name = data?.name ?? toSentenceCase(get(parsedProtocol));

  if (name.toLocaleLowerCase() === 'address') {
    return t('common.blockchain');
  }

  return name;
});
</script>

<template>
  <RuiTooltip
    :disabled="!shouldShowAmount"
    :open-delay="100"
    persist-on-tooltip-hover
    tooltip-class="!-ml-1"
  >
    <template #activator>
      <ProtocolIcon
        :protocol="transformedProtocol"
        :size="20"
        hide-tooltip
      />
    </template>

    <div class="flex flex-col gap-0.5">
      <div class="font-medium text-sm mb-0.5">
        {{ name }}
        <div
          v-if="protocolBalance.containsManual"
          class="font-normal text-caption"
        >
          {{ t('protocol_icon.contains_manual') }}
        </div>
      </div>
      <div
        v-if="proxyAddress"
        class="flex items-center gap-1"
      >
        <span class="text-rui-dark-text">{{ t('protocol_icon.ds_proxy') }}</span>
        <HashLink
          :text="proxyAddress"
          :location="Blockchain.ETH"
          display-mode="link"
        />
      </div>
      <AssetAmountDisplay
        v-if="asset"
        :asset="asset"
        :amount="protocolBalance.amount"
        :loading="loading"
        data-cy="top-protocol-amount"
      />
      <ValueDisplay
        v-else
        :value="protocolBalance.amount"
        :loading="loading"
        data-cy="top-protocol-amount"
      />
      <FiatDisplay
        :value="protocolBalance.value"
        :loading="loading"
        data-cy="top-protocol-value"
      />
    </div>
  </RuiTooltip>
</template>
