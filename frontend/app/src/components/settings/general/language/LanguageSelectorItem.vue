<script setup lang="ts">
import Flag from '@/components/common/Flag.vue';

defineProps<{
  countries: string[];
  label: string;
}>();
</script>

<template>
  <div class="flex items-center">
    <div class="ml-1 flex items-center">
      <div
        v-for="(country, index) in countries"
        :key="country"
        class="flex items-center"
      >
        <span
          v-if="index > 0"
          class="px-1"
        >
          /
        </span>
        <Flag :iso="country" />
      </div>
    </div>
    <div class="ml-3">
      {{ label }}
    </div>
  </div>
</template>
