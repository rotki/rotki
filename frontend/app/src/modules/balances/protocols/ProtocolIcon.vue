<script setup lang="ts">
import { Blockchain, toSentenceCase } from '@rotki/common';
import { useProtocolData } from '@/modules/balances/protocols/use-protocol-data';
import { useProxyProtocol } from '@/modules/balances/protocols/use-proxy-protocol';
import HashLink from '@/modules/shell/components/HashLink.vue';
import IconMark from '@/modules/shell/components/IconMark.vue';

const { protocol, hideTooltip } = defineProps<{
  protocol: string;
  hideTooltip?: boolean;
}>();

defineSlots<{
  default?: (props: { protocol: string }) => any;
}>();

const { isProxy, parsedProtocol, proxyAddress } = useProxyProtocol(() => protocol);

const showTooltip = computed<boolean>(() => get(isProxy) && !!get(proxyAddress) && !hideTooltip);

const { protocolData } = useProtocolData(parsedProtocol);

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RuiTooltip
    :options="{ placement: 'top' }"
    :open-delay="400"
    :disabled="!showTooltip"
  >
    <template #activator>
      <div
        class="rounded-full overflow-hidden size-7 shrink-0 flex items-center justify-center"
        :class="{ relative: isProxy }"
      >
        <RuiIcon
          v-if="protocolData?.type === 'icon'"
          color="secondary"
          size="16"
          :name="protocolData.icon"
        />
        <IconMark
          v-else-if="protocolData?.type === 'image'"
          :src="protocolData.image"
          :alt="protocolData.name"
          size="28px"
        />
        <RuiIcon
          v-else
          name="lu-blocks"
          color="secondary"
          size="16"
        />
        <div
          v-if="isProxy"
          class="absolute right-0 top-0 h-full w-1/2 bg-rui-grey-300/90 dark:bg-rui-grey-600/90 flex items-center justify-center"
        >
          <RuiIcon
            name="lu-network"
            size="10"
          />
        </div>
      </div>
    </template>
    <div class="flex flex-col gap-1">
      <div class="font-medium text-sm">
        {{ protocolData?.name ?? toSentenceCase(parsedProtocol) }}
      </div>
      <div
        v-if="proxyAddress"
        class="flex items-center gap-1"
      >
        <span>{{ t('protocol_icon.ds_proxy') }}</span>
        <HashLink
          :text="proxyAddress"
          :location="Blockchain.ETH"
          display-mode="link"
        />
      </div>
    </div>
  </RuiTooltip>
  <slot :protocol="protocolData?.name ?? toSentenceCase(parsedProtocol)" />
</template>
