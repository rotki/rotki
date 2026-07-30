<script setup lang="ts">
type Style = Record<string, string>;

interface Dimension {
  value: number;
  unit: string;
}

const {
  asset = '',
  blockie,
  customAsset,
  size,
} = defineProps<{
  size: string;
  asset?: string;
  customAsset?: boolean;
  /**
   * Blockie data URI to render instead of the text mark. Used when there is no symbol or name to
   * take initials from, where the text would otherwise be the first characters of a raw
   * identifier — the same `eip` for every unknown EVM asset.
   */
  blockie?: string;
}>();

const dimensions = computed<Dimension>(() => {
  const match: RegExpMatchArray | null = size.match(/^(\d+(?:\.\d)?)(\w+|%)?$/);
  const value: string = match?.[1] ?? '0';
  const unit: string = match?.[2] ?? '';
  return {
    unit,
    value: Number(value),
  };
});

const wrapperStyle = computed<Style>(() => ({
  height: size,
  minHeight: size,
  minWidth: size,
  width: size,
}));

const text = computed<string>(() => {
  if (asset.length > 3)
    return asset.slice(0, 3);

  return asset;
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
    <img
      v-else-if="blockie"
      :src="blockie"
      :style="wrapperStyle"
      alt=""
      class="rounded-full"
    />
    <template v-else>
      {{ text }}
    </template>
  </span>
</template>
