<script setup lang="ts">
import { type DefiProtocol } from '@rotki/common/lib/blockchain';

interface DefiProtocolInfo {
  readonly identifier: string;
  readonly label?: string;
  readonly protocol: DefiProtocol;
}

const props = defineProps<{
  item: DefiProtocolInfo;
}>();
const { item } = toRefs(props);

const getIcon = ({ protocol }: DefiProtocolInfo): string =>
  protocol.startsWith('makerdao') ? 'makerdao' : protocol;
</script>

<template>
  <div class="flex flex-row items-center">
    <VImg
      aspect-ratio="1"
      contain
      position="left"
      width="26px"
      max-height="24px"
      :src="`./assets/images/protocols/${getIcon(item)}.svg`"
    />
    <span class="ml-2">{{ item.label ?? item.identifier }}</span>
  </div>
</template>
