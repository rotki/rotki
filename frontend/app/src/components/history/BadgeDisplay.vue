<script setup lang="ts">
import { useListeners } from 'vue';

defineProps({
  color: { required: false, type: String, default: 'grey-darken' }
});
const rootAttrs = useAttrs();
const rootListeners = useListeners();
</script>

<template>
  <VChip
    small
    :color="`${color} lighten-5`"
    :text-color="color"
    class="font-black rounded py-0 px-2 text-overline"
    v-bind="rootAttrs"
    v-on="rootListeners"
  >
    <slot />
  </VChip>
</template>
