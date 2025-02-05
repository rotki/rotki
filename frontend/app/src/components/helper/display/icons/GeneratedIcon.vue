<script setup lang="ts">
type Style = Record<string, string>;

interface Dimension {
  value: number;
  unit: string;
}

const props = withDefaults(
  defineProps<{
    size: string;
    asset?: string;
    customAsset?: boolean;
    flat?: boolean;
  }>(),
  {
    asset: '',
    customAsset: false,
    flat: false,
  },
);

const { asset, size } = toRefs(props);

const dimensions = computed<Dimension>(() => {
  const match: RegExpMatchArray | null = get(size).match(/^(\d+(?:\.\d)?)(\w+|%)?$/);
  const value: string = match?.[1] ?? '0';
  const unit: string = match?.[2] ?? '';
  return {
    unit,
    value: Number(value),
  };
});

const wrapperStyle = computed<Style>(() => ({
  height: get(size),
  minHeight: get(size),
  minWidth: get(size),
  width: get(size),
}));

const text = computed<string>(() => {
  if (get(asset).length > 3)
    return get(asset).slice(0, 3);

  return get(asset);
});

const textStyle = computed<Style>(() => {
  const length = get(text).length;
  const { value } = get(dimensions);

  const fontSize = (value - 2) / Math.max(length, length < 2 ? 1.8 : 2.5);

  return {
    fontSize: `${fontSize}px`,
  };
});

const customIconSize = computed(() => {
  const { value } = get(dimensions);

  return Math.min(24, value / 2);
});
</script>

<template>
  <span
    :style="{ ...wrapperStyle, ...textStyle }"
    class="flex items-center justify-center rounded-full whitespace-nowrap tracking-normal font-semibold bg-rui-grey-200 dark:bg-rui-grey-300 text-rui-grey-600 dark:text-rui-grey-700 border border-rui-grey-300 dark:border-rui-grey-400 uppercase"
  >
    <RuiIcon
      v-if="customAsset"
      :size="customIconSize"
      name="lu-pencil"
    />
    <template v-else>
      {{ text }}
    </template>
  </span>
</template>
