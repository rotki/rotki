<script setup lang="ts">
import { useBankConnectionsStore } from '@/modules/banks/use-bank-connections-store';
import { getPublicProtocolImagePath } from '@/modules/core/common/file/file';
import LocationIcon from '@/modules/shell/components/display/LocationIcon.vue';
import IconMark from '@/modules/shell/components/IconMark.vue';

/** A bank connector's logo, or the shared bank icon for a connector without one, such as FinTS. */
const { connector, size = '20px' } = defineProps<{
  connector: string;
  size?: string;
}>();

const { bankNameFor, manifestFor } = useBankConnectionsStore();

const image = computed<string | undefined>(() => {
  const file = manifestFor(connector)?.image;
  return file ? getPublicProtocolImagePath(file) : undefined;
});
</script>

<template>
  <IconMark
    v-if="image"
    :src="image"
    :alt="bankNameFor(connector)"
    :size="size"
    data-testid="bank-connector-icon"
    :data-connector="connector"
  />
  <LocationIcon
    v-else
    item="banks"
    icon
    :size="size"
    data-testid="bank-connector-icon"
    :data-connector="connector"
  />
</template>
