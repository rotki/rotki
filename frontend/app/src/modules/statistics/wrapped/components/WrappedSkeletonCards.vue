<script setup lang="ts">
import WrappedCard from './WrappedCard.vue';
import WrappedHighlight from './WrappedHighlight.vue';

/** The loaded page's shape: the headline figures, then the lists two to a row. */
const {
  count = 4,
} = defineProps<{
  count?: number;
}>();

const rows = new Array(5).fill({});

/** A label that keeps its line, so the skeleton tiles are as tall as the loaded ones. */
const BLANK_LABEL = ' ';
</script>

<template>
  <div class="grid gap-4 md:grid-cols-2 lg:grid-cols-4 max-md:gap-0 max-md:rounded-rui-card max-md:border max-md:border-rui-divider max-md:bg-rui-surface">
    <WrappedHighlight
      v-for="i in 4"
      :key="i"
      :label="BLANK_LABEL"
    >
      <RuiSkeletonLoader class="w-32 h-7" />
    </WrappedHighlight>
  </div>
  <div class="grid gap-4 lg:grid-cols-2">
    <WrappedCard
      v-for="i in count"
      :key="i"
      :items="rows"
    >
      <template #header-icon>
        <RuiSkeletonLoader class="size-4" />
      </template>
      <template #header>
        <RuiSkeletonLoader class="w-48" />
      </template>
      <template #label>
        <RuiSkeletonLoader class="w-32" />
      </template>
      <template #value>
        <RuiSkeletonLoader class="w-20" />
      </template>
    </WrappedCard>
  </div>
</template>
