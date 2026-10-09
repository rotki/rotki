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
  identifier,
  size,
} = defineProps<{
  size: string;
  asset?: string;
  /** Seeds the colour, so two assets sharing a symbol still tell apart; the text when absent. */
  identifier?: string;
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

/** Small icons fit two letters without clipping; larger ones keep three. */
const SMALL_ICON = 26;

const text = computed<string>(() => {
  const letters = get(dimensions).value <= SMALL_ICON ? 2 : 3;
  return asset.slice(0, letters);
});

/**
 * A hue taken from the identifier, so one asset always gets the same colour, neighbours in a stack
 * tell apart at a glance, and a token bridged to another chain gets its own.
 */
const hue = computed<number>(() => {
  let hash = 0;
  for (const char of (identifier ?? asset).toUpperCase())
    hash = (hash * 31 + char.charCodeAt(0)) % 360;
  return hash;
});

/** Only the lettered mark is tinted; the custom-asset pencil and the blockie stay neutral. */
const tinted = computed<boolean>(() => !customAsset && !blockie && asset.length > 0);

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
    :style="{ ...wrapperStyle, ...textStyle, '--generated-hue': hue }"
    class="flex items-center justify-center rounded-full whitespace-nowrap tracking-normal font-semibold uppercase"
    :class="tinted
      ? 'bg-[hsl(var(--generated-hue)_65%_91%)] text-[hsl(var(--generated-hue)_55%_32%)] dark:bg-[hsl(var(--generated-hue)_35%_26%)] dark:text-[hsl(var(--generated-hue)_70%_82%)]'
      : 'bg-rui-grey-200 dark:bg-rui-grey-300 text-rui-grey-600 dark:text-rui-grey-700 border border-rui-grey-300 dark:border-rui-grey-400'"
    data-testid="generated-icon"
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
