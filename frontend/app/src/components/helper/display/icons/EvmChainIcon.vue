<script setup lang="ts">
import { type EvmChain } from '@rotki/common/lib/data';
import { getChainData } from '@/types/blockchain/chains';

interface Props {
  size?: string;
  chain: EvmChain;
  tooltip?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  size: '24px'
});

const { chain } = toRefs(props);

const chainData = computed(() => {
  return getChainData(get(chain));
});

const css = useCssModule();
</script>
<template>
  <v-tooltip v-if="chainData" top :disabled="!tooltip">
    <template #activator="{ on }">
      <v-img
        :class="css.circle"
        :src="chainData.image"
        :width="size"
        :max-width="size"
        :height="size"
        :max-height="size"
        contain
        v-on="on"
      />
    </template>
    <span>{{ chainData.label }}</span>
  </v-tooltip>
</template>
<style lang="scss" module>
.circle {
  border-radius: 50%;
  overflow: hidden;
}
</style>
