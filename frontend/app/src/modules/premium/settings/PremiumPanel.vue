<script setup lang="ts">
const { description, title } = defineProps<{
  /** Left out where the content leads with its own heading. */
  title?: string;
  description?: string;
}>();

defineSlots<{
  'default': () => any;
  'header-append'?: () => any;
  'actions'?: () => any;
}>();
</script>

<template>
  <section class="flex flex-col rounded-rui-card border border-rui-divider bg-rui-surface overflow-clip">
    <header
      v-if="title || $slots['header-append']"
      class="flex flex-wrap items-start justify-between gap-x-4 gap-y-2 px-4 pt-4"
    >
      <div class="flex flex-col gap-1 min-w-0">
        <h2
          v-if="title"
          class="m-0 text-base font-semibold text-rui-text"
        >
          {{ title }}
        </h2>
        <p
          v-if="description"
          class="m-0 text-sm text-rui-text-secondary"
        >
          {{ description }}
        </p>
      </div>
      <slot name="header-append" />
    </header>
    <div class="flex flex-col gap-4 p-4 grow">
      <slot />
    </div>
    <footer
      v-if="$slots.actions"
      class="flex flex-wrap items-center justify-end gap-2 px-4 py-3 border-t border-rui-divider"
    >
      <slot name="actions" />
    </footer>
  </section>
</template>
