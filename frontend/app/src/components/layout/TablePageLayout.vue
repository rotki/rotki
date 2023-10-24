<script setup lang="ts">
withDefaults(
  defineProps<{ hideHeader?: boolean; child?: boolean; title?: string[] }>(),
  {
    title: undefined
  }
);
</script>

<template>
  <div :class="{ container: !child }">
    <div class="flex flex-col gap-4">
      <div
        v-if="!hideHeader"
        class="flex flex-row flex-wrap items-center gap-4 min-h-[2.25rem]"
      >
        <div class="text-body-1 text-rui-text">
          <slot name="title">
            <template v-for="(item, index) in title">
              <span
                v-if="index < title.length - 1"
                :key="index.toString()"
                class="text-rui-text-secondary"
              >
                {{ item }} /
              </span>
              <template v-else>
                {{ item }}
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
