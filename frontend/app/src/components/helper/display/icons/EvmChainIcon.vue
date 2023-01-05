<script setup lang="ts">
import { toCapitalCase } from '@/utils/text';

interface Props {
  size?: string;
  chain: string;
  tooltip?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  size: '24px'
});

const { chain } = toRefs(props);

const { evmChainNames } = useSupportedChains();

const getImageUrl = (evmChain: string): string => {
  return `./assets/images/chains/${evmChain}.svg`;
};

const chainData = computed(() => {
  const names = get(evmChainNames);
  const chainProp = get(chain);
  const evmChain = names.find(x => x === chainProp);

  if (!evmChain) {
    return null;
  }

  return {
    label: toCapitalCase(evmChain),
    image: getImageUrl(evmChain)
  };
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
