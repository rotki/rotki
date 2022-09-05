<template>
  <v-chip
    small
    :color="`${color} lighten-5`"
    :text-color="color"
    class="font-weight-black rounded py-0 px-2 text-overline"
    v-bind="rootAttrs"
    v-on="rootListeners"
  >
    <slot />
  </v-chip>
</template>
<script setup lang="ts">
import { useAttrs, useListeners } from 'vue';

const rootAttrs = useAttrs();
const rootListeners = useListeners();

defineProps({
  color: { required: false, type: String, default: 'grey-darken' }
});
</script>
