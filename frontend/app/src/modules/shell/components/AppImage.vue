<script setup lang="ts">
import { toRem } from '@/modules/core/common/data/data';
import { getPublicPlaceholderImagePath } from '@/modules/core/common/file/file';

const {
  alt,
  contain = false,
  cover = false,
  height,
  imageClass,
  loading = false,
  maxHeight,
  maxWidth,
  size,
  sizes,
  src,
  srcset,
  width,
} = defineProps<{
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
  cover?: boolean;
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
      :class="[{ 'object-contain': contain, 'object-cover': cover }, imageClass]"
      loading="lazy"
      :style="style"
      :sizes="sizes"
      :srcset="srcset"
    />
    <img
      v-else
      :alt="alt"
      :class="[{ 'object-contain': contain, 'object-cover': cover }, imageClass]"
      :style="style"
      :src="src"
      :sizes="sizes"
      :srcset="srcset"
      loading="lazy"
      @error="onError()"
      @loadstart="onLoadStart()"
      @load="onLoad()"
    />
  </div>
</template>
