<template>
  <v-img
    v-if="error"
    :width="width"
    :height="height"
    contain
    src="./assets/images/rotkehlchen_no_text.png"
  />
  <v-img
    v-else
    :width="width"
    :height="height"
    contain
    :src="url"
    @loadstart="error = false"
    @load="error = false"
    @error="error = true"
  />
</template>
<script setup lang="ts">
import { Ref } from 'vue';

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
</script>
