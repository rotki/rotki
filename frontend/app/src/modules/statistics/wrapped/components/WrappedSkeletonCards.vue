<script setup lang="ts">
import WrappedCard from './WrappedCard.vue';

withDefaults(defineProps<{
  count?: number;
}>(), {
  count: 3,
});
</script>

<template>
  <template
    v-for="i in count"
    :key="i"
  >
    <WrappedCard
      :items="new Array(3).fill({})"
    >
      <template #header-icon>
        <RuiSkeletonLoader class="size-6" />
      </template>
      <template #header>
        <RuiSkeletonLoader class="w-60" />
      </template>
      <template #label>
        <RuiSkeletonLoader class="w-20" />
      </template>
      <template #value>
        <RuiSkeletonLoader class="w-20" />
      </template>
    </WrappedCard>
  </template>
</template>
