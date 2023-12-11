<script setup lang="ts">
import { type MaybeRef } from '@vueuse/core';
import { type Ref } from 'vue';
import { toRem } from '@/utils/data';

const props = withDefaults(
  defineProps<{
    width?: string | number;
    height?: string | number;
    maxWidth?: string | number;
    maxHeight?: string | number;
    size?: string | number;
    src?: string;
    srcset?: string;
    sizes?: string;
    alt?: string;
    contain?: boolean;
  }>(),
  {
    width: undefined,
    height: undefined,
    maxWidth: undefined,
    maxHeight: undefined,
    size: undefined,
    src: undefined,
    sizes: undefined,
    srcset: undefined,
    alt: undefined,
    contain: false
  }
);

const css = useCssModule();

const { width, height, maxWidth, maxHeight, size } = toRefs(props);

const error: Ref<boolean> = ref(false);
const success: Ref<boolean> = ref(false);

const style = computed(() => ({
  width: getSizeOrValue(get(width)),
  height: getSizeOrValue(get(height)),
  maxWidth: getSizeOrValue(get(maxWidth)),
  maxHeight: getSizeOrValue(get(maxHeight))
}));

const getSizeOrValue = (value: MaybeRef<string | number>) =>
  isDefined(get(size)) ? toRem(get(size)) : toRem(get(value));
</script>

<template>
  <div :class="css.wrapper">
    <img
      :alt="alt"
      :class="{ 'object-contain': contain }"
      :style="style"
      :src="src"
      :sizes="sizes"
      :srcset="srcset"
      @error="error = true"
      @load="
        error = false;
        success = true;
      "
      @loadstart="error = false"
    />
  </div>
</template>

<style module lang="scss">
.wrapper {
  @apply flex;
}
</style>
