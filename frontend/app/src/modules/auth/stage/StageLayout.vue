<script setup lang="ts">
const { wide = false } = defineProps<{
  /** Widens the column for a stage that lays out a comparison, like the asset conflicts. */
  wide?: boolean;
}>();

defineSlots<{
  title: () => any;
  subtitle?: () => any;
  default?: () => any;
  actions?: () => any;
}>();
</script>

<template>
  <section
    class="w-full mx-auto flex flex-col gap-6 text-pretty"
    :class="wide ? 'max-w-200' : 'max-w-120'"
  >
    <header>
      <h1
        class="text-h4 mb-2"
        data-testid="stage-title"
      >
        <slot name="title" />
      </h1>
      <div
        v-if="$slots.subtitle"
        class="text-body-1 text-rui-text-secondary break-words"
        data-testid="stage-subtitle"
      >
        <slot name="subtitle" />
      </div>
    </header>

    <slot />

    <div
      v-if="$slots.actions"
      class="flex flex-wrap gap-2"
    >
      <slot name="actions" />
    </div>
  </section>
</template>
