<script setup lang="ts">
import { toSentenceCase } from '@rotki/common';
import AppImage from '@/components/common/AppImage.vue';
import { useProtocolData } from '@/modules/balances/protocols/use-protocol-data';

const props = defineProps<{
  protocol: string;
  size?: number;
  loading?: boolean;
}>();

defineSlots<{
  default?: (props: { protocol: string }) => any;
}>();

const { protocol, size = 20 } = toRefs(props);
const { protocolData } = useProtocolData(protocol);
</script>

<template>
  <div class="rounded-full overflow-hidden size-8 flex items-center justify-center border bg-white border-rui-grey-300 dark:border-rui-grey-700">
    <RuiIcon
      v-if="protocolData?.type === 'icon'"
      color="secondary"
      :size="size"
      :name="protocolData.icon"
    />
    <AppImage
      v-else-if="protocolData?.type === 'image'"
      class="icon-bg rounded-full overflow-hidden"
      :src="protocolData.image"
      size="24px"
      :loading="loading"
      contain
    />
    <RuiIcon
      v-else
      name="lu-blocks"
      color="secondary"
      :size="size"
    />
  </div>
  <slot :protocol="protocolData?.name ?? toSentenceCase(protocol)" />
</template>
