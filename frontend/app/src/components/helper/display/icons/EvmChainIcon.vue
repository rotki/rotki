<script setup lang="ts">
interface Props {
  size?: string;
  chain: string;
  tooltip?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  size: '24px',
  tooltip: false
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
    :disabled="!tooltip"
    :popper="{ placement: 'top' }"
    :open-delay="400"
  >
    <template #activator>
      <AppImage :size="size" :src="chainData.image" :alt="chainData.label" />
    </template>
    {{ chainData.label }}
  </RuiTooltip>
</template>
