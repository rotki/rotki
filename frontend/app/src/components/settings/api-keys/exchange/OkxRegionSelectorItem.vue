<script setup lang="ts">
import type { OkxLocation } from '@/types/exchanges';
import Flag from '@/components/common/Flag.vue';

defineProps<{
  identifier: OkxLocation;
  label: string;
}>();
</script>

<template>
  <div class="flex items-center gap-3">
    <template v-if="identifier === 'global'">
      <RuiIcon
        name="lu-globe"
        size="18"
        class="mx-0.5 text-rui-text-secondary"
      />
    </template>
    <template v-else-if="identifier === 'eea'">
      <Flag iso="eu" />
    </template>
    <template v-else-if="identifier === 'us'">
      <Flag iso="us" />
    </template>
    <span>{{ label }}</span>
  </div>
</template>
