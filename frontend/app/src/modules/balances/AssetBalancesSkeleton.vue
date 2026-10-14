<script setup lang="ts">
/** Stands in for an asset table on its first load, shaped like its rows so nothing jumps when they arrive. */
const { rows = 5 } = defineProps<{
  rows?: number;
}>();
</script>

<template>
  <div
    class="flex flex-col"
    aria-hidden="true"
    data-testid="asset-balances-skeleton"
  >
    <div class="h-11 bg-rui-surface-muted border-b border-rui-divider" />
    <div class="between:border-t between:border-rui-divider">
      <div
        v-for="row in rows"
        :key="row"
        class="flex items-center gap-4 h-18 px-4"
      >
        <RuiSkeletonLoader
          type="avatar"
          class="size-8 shrink-0"
        />
        <div class="flex flex-col gap-2 w-40">
          <RuiSkeletonLoader class="w-16" />
          <RuiSkeletonLoader class="w-28 h-3" />
        </div>
        <div class="ml-auto flex items-center gap-12 pr-16">
          <RuiSkeletonLoader class="w-20 max-md:hidden" />
          <RuiSkeletonLoader class="w-24" />
          <RuiSkeletonLoader class="w-24" />
        </div>
      </div>
    </div>
  </div>
</template>
