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

const style = computed(() => ({
  'max-height': props.size,
  'max-width': props.size
}));
</script>

<template>
  <RuiTooltip v-if="tooltip" :popper="{ placement: 'top' }" open-delay="400">
    <template #activator>
      <img
        :class="{
          'rounded-full overflow-hidden': !tile
        }"
        :style="style"
        class="object-contain"
        :src="chainData.image"
        :alt="chainData.label"
      />
    </template>
    {{ chainData.label }}
  </RuiTooltip>
  <img
    v-else
    :class="{
      'rounded-full overflow-hidden': !tile
    }"
    :style="style"
    class="object-contain"
    :height="size"
    :width="size"
    :src="chainData.image"
    :alt="chainData.label"
  />
</template>

<style lang="scss" module>
.image {
  max-height: v-bind(size);
  max-width: v-bind(size);
}
</style>
