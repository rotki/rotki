<script setup lang="ts">
const { hideHeader, child, title } = defineProps<{ hideHeader?: boolean; child?: boolean; title?: string[] }>();

const slots = defineSlots<{
  default?: () => unknown;
  title?: () => unknown;
  buttons?: () => unknown;
  tabs?: () => unknown;
}>();

const hasTabs = computed<boolean>(() => Boolean(slots.tabs));

const lastTitleIndex = computed<number>(() => (title?.length ?? 0) - 1);
</script>

<template>
  <div :class="{ container: !child }">
    <div class="flex flex-col gap-4">
      <div
        v-if="!hideHeader"
        class="flex flex-wrap items-center gap-2 lg:gap-4 min-h-[2.25rem]"
      >
        <div
          v-if="title"
          class="text-sm text-rui-text flex items-center font-medium"
        >
          <slot name="title">
            <template
              v-for="(item, index) in title"
              :key="index"
            >
              <span
                v-if="index < lastTitleIndex"
                class="text-rui-text-secondary flex items-center"
              >
                {{ item }}
                <RuiIcon
                  name="lu-chevron-right"
                  size="16"
                  class="mx-2"
                />
              </span>
              <span
                v-else
                class="bg-rui-grey-200 dark:bg-rui-grey-900 text-rui-text-secondary rounded-md px-2 py-1"
              >
                {{ item }}
              </span>
            </template>
          </slot>
        </div>
        <div class="hidden sm:block sm:grow" />
        <slot name="buttons" />
      </div>
      <slot name="tabs" />
      <div
        class="flex flex-col gap-4"
        :class="{ '-mt-2': hasTabs }"
      >
        <slot />
      </div>
    </div>
  </div>
</template>
