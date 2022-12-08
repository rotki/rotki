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
    :src="remoteLogo"
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
  }
});

const error: Ref<boolean> = ref(false);
const remoteLogo =
  'https://raw.githubusercontent.com/rotki/rotki/develop/frontend/app/public/remote/logo.png';
</script>
