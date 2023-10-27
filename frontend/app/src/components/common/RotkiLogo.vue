<script setup lang="ts">
import { type Ref } from 'vue';

withDefaults(
  defineProps<{
    width?: string | number;
    height?: string | number;
    url?: string;
  }>(),
  {
    width: 'auto',
    height: 'auto',
    url: undefined
  }
);

const error: Ref<boolean> = ref(false);
const success: Ref<boolean> = ref(false);
</script>

<template>
  <div>
    <img
      v-if="error || !success"
      alt="logo"
      :width="width"
      :height="height"
      class="object-contain"
      src="/assets/images/rotkehlchen_no_text.png"
    />
    <img
      alt="logo"
      :width="width"
      :height="success ? height : 0"
      class="object-contain"
      :src="url"
      @loadstart="error = false"
      @load="
        error = false;
        success = true;
      "
      @error="error = true"
    />
  </div>
</template>
