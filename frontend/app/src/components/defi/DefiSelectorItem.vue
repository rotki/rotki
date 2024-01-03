<script setup lang="ts">
import { type DefiProtocol } from '@/types/modules';

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
  <div class="flex flex-row items-center gap-2">
    <AppImage
      contain
      size="24px"
      :src="`./assets/images/protocols/${getIcon(item)}.svg`"
    />
    {{ item.label ?? item.identifier }}
  </div>
</template>
