<script setup lang="ts">
import { toRem } from '@/modules/core/common/data/data';
import { getPublicPlaceholderImagePath } from '@/modules/core/common/file/file';
import { fillsFrame } from '@/modules/shell/components/icon-mark-shape';

/**
 * A logo in a circle of exactly `size`, the one shape every chain, location, protocol and asset logo
 * takes, in both themes.
 *
 * The frame owns the geometry: it is border-box, so the inset sits inside `size` rather than
 * growing the mark, and the image fills what is left with `object-contain`, which keeps it centered
 * whatever its own proportions.
 *
 * A logo that fills the circle by itself (a full-bleed square, or one with its own disc) is cropped
 * to it and reads as a disc in its own colours. A glyph on a transparent ground gets a backing so it
 * reads as a circle too: a faint tint ringed by a hairline on a light page, darker than whatever
 * surface it sits on (a white table row or a grey tile alike) and drawn to the same size as a logo
 * that fills its circle, white on a dark one so its dark strokes stay
 * visible, or black for a logo drawn for dark pages (`backing="dark"`).
 *
 * Only for raster or SVG logos: generated text icons, blockies and line icons are already drawn for
 * both themes and take no frame.
 */
const { alt, backing = 'light', loading = false, size, src } = defineProps<{
  src?: string;
  alt?: string;
  size: string | number;
  backing?: 'light' | 'dark';
  loading?: boolean;
}>();

const emit = defineEmits<{
  error: [];
  load: [];
  loadstart: [];
}>();

const failed = ref<boolean>(false);
/** Asks for a CORS response so the edges can be read; dropped for a host that refuses it. */
const crossOrigin = ref<boolean>(true);
const fills = ref<boolean>(false);

/**
 * The inset is worked out from the mark's own size: a percentage padding resolves against the width
 * of whatever contains the mark, a whole table cell included.
 */
const frameStyle = computed<{ height?: string; padding?: string; width?: string }>(() => {
  const value = toRem(size);
  return {
    height: value,
    padding: get(fills) ? undefined : `max(1px, calc(${value} * 0.08))`,
    width: value,
  };
});

const imageSrc = computed<string | undefined>(() => (get(failed) ? getPublicPlaceholderImagePath('image.svg') : src));

const frameClass = computed<string>(() => {
  if (get(fills))
    return '';
  return backing === 'dark'
    ? 'bg-rui-neutral-950/[0.06] shadow-[inset_0_0_0_1px_rgb(0_0_0/0.12)] dark:bg-black dark:shadow-none'
    : 'bg-rui-neutral-950/[0.06] shadow-[inset_0_0_0_1px_rgb(0_0_0/0.12)] dark:bg-white dark:shadow-none';
});

watch(() => src, () => {
  set(failed, false);
  set(crossOrigin, true);
  set(fills, false);
});

function onLoad(event: Event): void {
  const image = event.target;
  if (image instanceof HTMLImageElement && get(crossOrigin) && !get(failed))
    set(fills, fillsFrame(image));
  emit('load');
}

function onError(): void {
  if (get(crossOrigin)) {
    set(crossOrigin, false);
    return;
  }
  set(failed, true);
  emit('error');
}
</script>

<template>
  <span
    class="inline-flex shrink-0 items-center justify-center overflow-hidden rounded-full"
    :class="frameClass"
    :style="frameStyle"
    data-testid="icon-mark"
  >
    <RuiSkeletonLoader
      v-if="loading"
      class="size-full rounded-full"
    />
    <img
      v-else-if="imageSrc"
      :key="crossOrigin ? 'cors' : 'plain'"
      :src="imageSrc"
      :alt="alt"
      :crossorigin="crossOrigin ? 'anonymous' : undefined"
      class="size-full"
      :class="fills ? 'object-cover' : 'object-contain'"
      loading="lazy"
      @error="onError()"
      @loadstart="emit('loadstart')"
      @load="onLoad($event)"
    />
  </span>
</template>
