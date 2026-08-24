<script setup lang="ts">
const { variant } = defineProps<{
  variant: 'row' | 'card';
}>();

const card = computed<boolean>(() => variant === 'card');
</script>

<template>
  <div
    class="animate-pulse contain-content"
    :class="card ? 'p-3 border-b border-default' : 'h-[72px] flex items-center gap-4 border-b border-default px-4 pl-6'"
  >
    <template v-if="card">
      <!-- Top row: Event type with icon -->
      <div class="flex items-center gap-3 mb-2">
        <div class="size-10 rounded-full bg-rui-grey-300 dark:bg-rui-grey-700 shrink-0" />
        <div class="flex flex-col gap-1">
          <div class="h-4 w-20 rounded bg-rui-grey-300 dark:bg-rui-grey-700" />
          <div class="h-3 w-14 rounded bg-rui-grey-200 dark:bg-rui-grey-800" />
        </div>
      </div>
      <!-- Middle row: Asset & Amount -->
      <div class="flex items-center gap-2 mb-2">
        <div class="size-8 rounded-full bg-rui-grey-300 dark:bg-rui-grey-700" />
        <div class="flex flex-col gap-1">
          <div class="h-4 w-24 rounded bg-rui-grey-300 dark:bg-rui-grey-700" />
          <div class="h-3 w-16 rounded bg-rui-grey-200 dark:bg-rui-grey-800" />
        </div>
      </div>
      <!-- Bottom row: Notes -->
      <div class="h-3 w-3/4 rounded bg-rui-grey-200 dark:bg-rui-grey-800" />
    </template>
    <template v-else>
      <div class="w-56 shrink-0 flex items-center gap-3">
        <div class="size-10 rounded-full bg-rui-grey-300 dark:bg-rui-grey-700" />
        <div class="flex flex-col gap-1.5">
          <div class="h-4 w-20 rounded bg-rui-grey-300 dark:bg-rui-grey-700" />
          <div class="h-3 w-14 rounded bg-rui-grey-200 dark:bg-rui-grey-800" />
        </div>
      </div>
      <div class="w-56 xl:w-60 shrink-0 flex items-center gap-2">
        <div class="size-8 rounded-full bg-rui-grey-300 dark:bg-rui-grey-700" />
        <div class="flex flex-col gap-1.5">
          <div class="h-4 w-24 rounded bg-rui-grey-300 dark:bg-rui-grey-700" />
          <div class="h-3 w-16 rounded bg-rui-grey-200 dark:bg-rui-grey-800" />
        </div>
      </div>
      <div class="flex-1 min-w-0 flex flex-col gap-1.5">
        <div class="h-3.5 w-3/4 rounded bg-rui-grey-300 dark:bg-rui-grey-700" />
        <div class="h-3 w-1/2 rounded bg-rui-grey-200 dark:bg-rui-grey-800" />
      </div>
      <div class="w-24 shrink-0" />
    </template>
  </div>
</template>
