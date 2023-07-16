<script setup lang="ts">
interface Props {
  size?: string;
  chain: string;
  tile?: boolean;
  tooltip?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  size: '24px',
  tooltip: false,
  tile: false
});

const { chain } = toRefs(props);

const getImageUrl = (evmChain: string): string =>
  `./assets/images/protocols/${evmChain}.svg`;

const chainData = computed(() => {
  const chainProp = get(chain);

  return {
    label: toCapitalCase(chainProp),
    image: getImageUrl(chainProp)
  };
});

const css = useCssModule();
</script>

<template>
  <VTooltip v-if="chainData" top :disabled="!tooltip">
    <template #activator="{ on }">
      <VImg
        :class="{ [css.circle]: !tile }"
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
  </VTooltip>
</template>

<style lang="scss" module>
.circle {
  border-radius: 50%;
  overflow: hidden;
}
</style>
