<script setup lang="ts">
import { Blockchain, toSentenceCase } from '@rotki/common';
import AppImage from '@/components/common/AppImage.vue';
import { useProtocolData } from '@/modules/balances/protocols/use-protocol-data';
import { useProxyProtocol } from '@/modules/balances/protocols/use-proxy-protocol';
import HashLink from '@/modules/common/links/HashLink.vue';

const props = defineProps<{
  protocol: string;
  size?: number;
  hideTooltip?: boolean;
}>();

defineSlots<{
  default?: (props: { protocol: string }) => any;
}>();

const { protocol, size = 20 } = toRefs(props);

const { isProxy, parsedProtocol, proxyAddress } = useProxyProtocol(protocol);

const showTooltip = computed<boolean>(() => get(isProxy) && !!get(proxyAddress) && !props.hideTooltip);

const { protocolData } = useProtocolData(parsedProtocol);

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RuiTooltip
    :popper="{ placement: 'top' }"
    :open-delay="400"
    :disabled="!showTooltip"
  >
    <template #activator>
      <div
        class="rounded-full overflow-hidden size-8 flex items-center justify-center border bg-white border-rui-grey-300 dark:border-rui-grey-700"
        :class="{ relative: isProxy }"
      >
        <RuiIcon
          v-if="protocolData?.type === 'icon'"
          color="secondary"
          :size="size"
          :name="protocolData.icon"
        />
        <AppImage
          v-else-if="protocolData?.type === 'image'"
          class="rounded-full overflow-hidden"
          :src="protocolData.image"
          size="24px"
          contain
        />
        <RuiIcon
          v-else
          name="lu-blocks"
          color="secondary"
          :size="size"
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
