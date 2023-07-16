<script setup lang="ts">
import { type Ref } from 'vue';

defineProps({
  width: {
    required: false,
    type: [String, Number],
    default: 'auto'
  },
  height: {
    required: false,
    type: [String, Number],
    default: 'auto'
  },
  url: {
    required: false,
    type: String,
    default: null
  }
});

const error: Ref<boolean> = ref(false);
const success: Ref<boolean> = ref(false);
</script>

<template>
  <div>
    <VImg
      v-if="error || !success"
      :width="width"
      :height="height"
      contain
      src="./assets/images/rotkehlchen_no_text.png"
    />
    <VImg
      :width="width"
      :height="success ? height : 0"
      contain
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
