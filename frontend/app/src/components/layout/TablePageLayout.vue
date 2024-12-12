<script setup lang="ts">
withDefaults(defineProps<{ hideHeader?: boolean; child?: boolean; title?: string[] }>(), {
  title: undefined,
});
</script>

<template>
  <div :class="{ container: !child }">
    <div class="flex flex-col gap-4">
      <div
        v-if="!hideHeader"
        class="flex flex-row flex-wrap items-center gap-4 min-h-[2.25rem]"
      >
        <div
          v-if="title"
          class="text-sm text-rui-text flex items-center font-medium"
        >
          <slot name="title">
            <template v-for="(item, index) in title">
              <span
                v-if="title && index < title.length - 1"
                :key="index"
                class="text-rui-text-secondary flex items-center"
              >
                {{ item }}
                <RuiIcon
                  name="lu-chevron-right"
                  size="16"
                  class="mx-2"
                />
              </span>
              <template v-else>
                <span
                  :key="index"
                  class="bg-rui-grey-200 dark:bg-rui-grey-900 text-rui-text-secondary rounded-md px-2 py-1"
                >
                  {{ item }}
                </span>
              </template>
            </template>
          </slot>
        </div>
        <div class="hidden sm:block sm:grow" />
        <slot name="buttons" />
      </div>
      <slot />
    </div>
  </div>
</template>
