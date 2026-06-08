<script setup lang="ts">
import { useProtocolData } from '@/modules/balances/protocols/use-protocol-data';
import AppImage from '@/modules/shell/components/AppImage.vue';

// Resolves a single protocol's icon/image. Kept as its own component so the breakdown can
// render one per bucket row (useProtocolData must run at a component's setup, not in a loop).
const { protocol } = defineProps<{ protocol: string }>();

const { protocolData } = useProtocolData(() => protocol);
</script>

<template>
  <RuiIcon
    v-if="protocolData?.type === 'icon'"
    :name="protocolData.icon"
    size="16"
  />
  <AppImage
    v-else-if="protocolData?.type === 'image'"
    :src="protocolData.image"
    size="16px"
    contain
    class="rounded-full overflow-hidden"
  />
  <RuiIcon
    v-else
    name="lu-blocks"
    size="16"
  />
</template>
