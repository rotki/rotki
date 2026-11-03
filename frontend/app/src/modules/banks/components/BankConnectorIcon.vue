<script setup lang="ts">
import { fintsBankLogo } from '@/modules/banks/fints-bank-directory';
import { useBankConnectionsStore } from '@/modules/banks/use-bank-connections-store';
import { getPublicProtocolImagePath } from '@/modules/core/common/file/file';
import LocationIcon from '@/modules/shell/components/display/LocationIcon.vue';
import IconMark from '@/modules/shell/components/IconMark.vue';

/**
 * A bank's logo: the institution's when its bank code has one in the FinTS directory, else the
 * connector's, else the shared bank icon.
 */
const { bankCode, connector, size = '20px' } = defineProps<{
  connector: string;
  /** The institution's bank code (BLZ), for a connector such as FinTS that reaches many banks. */
  bankCode?: string | null;
  size?: string;
}>();

const { bankNameFor, manifestFor } = useBankConnectionsStore();

const image = computed<string | undefined>(() => {
  const file = (bankCode ? fintsBankLogo(bankCode) : undefined) ?? manifestFor(connector)?.image;
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
