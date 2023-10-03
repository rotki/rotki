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
</script>

<template>
  <RuiTooltip
    :popper="{ placement: 'top' }"
    open-delay="400"
    :disabled="!tooltip"
  >
    <template #activator>
      <VImg
        :class="{ 'rounded-full overflow-hidden': !tile }"
        :src="chainData.image"
        :width="size"
        :max-width="size"
        :height="size"
        :max-height="size"
        contain
      />
    </template>
    <span>{{ chainData.label }}</span>
  </RuiTooltip>
</template>
