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
    src?: string | null;
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

const emit = defineEmits<{
  (e: 'error'): void;
  (e: 'load'): void;
  (e: 'loadstart'): void;
}>();

const css = useCssModule();

const { width, height, maxWidth, maxHeight, size } = toRefs(props);

const error: Ref<boolean> = ref(false);
const success: Ref<boolean> = ref(false);

const style = computed(() => ({
  width: getSizeOrValue(width),
  height: getSizeOrValue(height),
  maxWidth: getSizeOrValue(maxWidth),
  maxHeight: getSizeOrValue(maxHeight)
}));

const getSizeOrValue = (value: MaybeRef<string | number | undefined>) =>
  isDefined(get(size)) ? toRem(get(size)) : toRem(get(value));

const onError = () => {
  set(error, true);
  emit('error');
};

const onLoad = () => {
  set(error, false);
  set(success, true);
  emit('load');
};

const onLoadStart = () => {
  set(error, false);
  emit('loadstart');
};
</script>

<template>
  <div :class="css.wrapper">
    <img
      :alt="alt"
      :class="{ 'object-contain': contain }"
      :style="style"
      :src="src || ''"
      :sizes="sizes"
      :srcset="srcset"
      @error="onError()"
      @loadstart="onLoadStart()"
      @load="onLoad()"
    />
  </div>
</template>

<style module lang="scss">
.wrapper {
  @apply flex;
}
</style>
