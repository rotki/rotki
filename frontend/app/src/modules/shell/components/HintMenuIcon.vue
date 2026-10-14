<script setup lang="ts">
defineOptions({
  inheritAttrs: false,
});

const { title } = defineProps<{
  /** A short heading over the explanation; most hints are a sentence or two and go without. */
  title?: string;
}>();

defineSlots<{
  default: () => any;
}>();
</script>

<template>
  <RuiMenu
    :class-names="{ menu: 'max-w-80' }"
    v-bind="$attrs"
  >
    <template #activator="{ attrs }">
      <RuiButton
        variant="text"
        icon
        class="text-rui-text-secondary!"
        v-bind="attrs"
      >
        <RuiIcon name="lu-circle-question-mark" />
      </RuiButton>
    </template>
    <div class="flex flex-col gap-1 px-4 py-3">
      <div
        v-if="title"
        class="text-sm font-semibold text-rui-text"
      >
        {{ title }}
      </div>
      <div class="text-sm leading-relaxed text-rui-text-secondary">
        <slot />
      </div>
    </div>
  </RuiMenu>
</template>
