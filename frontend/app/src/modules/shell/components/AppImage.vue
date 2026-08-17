<script setup lang="ts">
import { toRem } from '@/modules/core/common/data/data';
import { getPublicPlaceholderImagePath } from '@/modules/core/common/file/file';

const {
  alt,
  fit,
  height,
  imageClass,
  loading = false,
  maxHeight,
  maxWidth,
  size,
  src,
  width,
} = defineProps<{
  width?: string | number;
  height?: string | number;
  maxWidth?: string | number;
  maxHeight?: string | number;
  size?: string | number;
  src?: string;
  alt?: string;
  fit?: 'contain' | 'cover';
  loading?: boolean;
  imageClass?: string;
}>();

const emit = defineEmits<{
  error: [];
  load: [];
  loadstart: [];
}>();

const error = ref<boolean>(false);
const success = ref<boolean>(false);

const fitClass = computed<string | undefined>(() => {
  if (fit === undefined)
    return undefined;

  return fit === 'contain' ? 'object-contain' : 'object-cover';
});

const style = computed(() => ({
  height: getSizeOrValue(height),
  maxHeight: getSizeOrValue(maxHeight),
  maxWidth: getSizeOrValue(maxWidth),
  width: getSizeOrValue(width),
}));

function getSizeOrValue(value: string | number | undefined) {
  return size !== undefined ? toRem(size) : toRem(value);
}

function onError() {
  set(error, true);
  emit('error');
}

function onLoad() {
  set(error, false);
  set(success, true);
  emit('load');
}

function onLoadStart() {
  set(error, false);
  emit('loadstart');
}
</script>

<template>
  <div class="flex">
    <RuiSkeletonLoader
      v-if="loading"
      :style="style"
    />
    <img
      v-else-if="error"
      :src="getPublicPlaceholderImagePath('image.svg')"
      :class="[fitClass, imageClass]"
      loading="lazy"
      :style="style"
    />
    <img
      v-else
      :alt="alt"
      :class="[fitClass, imageClass]"
      :style="style"
      :src="src"
      loading="lazy"
      @error="onError()"
      @loadstart="onLoadStart()"
      @load="onLoad()"
    />
  </div>
</template>
