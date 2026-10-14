<script setup lang="ts">
/** One block of a settings popover: a short title, an optional line of context, then the control. */
defineProps<{
  title: string;
  description?: string;
}>();

defineSlots<{
  default?: () => unknown;
}>();
</script>

<template>
  <section class="flex flex-col gap-3">
    <div class="flex flex-col gap-0.5">
      <h4 class="text-sm font-semibold text-rui-text">
        {{ title }}
      </h4>
      <p
        v-if="description"
        class="text-xs text-rui-text-secondary"
      >
        {{ description }}
      </p>
    </div>
    <slot />
  </section>
</template>
