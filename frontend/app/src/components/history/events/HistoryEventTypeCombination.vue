<script setup lang="ts">
import { type ActionDataEntry } from '@/types/action';

withDefaults(
  defineProps<{
    type: ActionDataEntry;
    showLabel: boolean;
  }>(),
  {
    showLabel: false
  }
);

const { dark } = useTheme();
</script>

<template>
  <div class="flex items-center gap-3">
    <VAvatar
      class="text--darken-4"
      :color="dark ? 'white' : 'grey lighten-3'"
      :size="36"
    >
      <VIcon :size="20" :color="type.color || 'grey darken-2'">
        {{ type.icon }}
      </VIcon>
    </VAvatar>
    <div v-if="showLabel" class="font-bold text-uppercase text-sm">
      {{ type.label }}
    </div>
  </div>
</template>
