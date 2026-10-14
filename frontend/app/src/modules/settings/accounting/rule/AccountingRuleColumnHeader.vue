<script setup lang="ts">
/**
 * A rule-table column header that wraps onto a second line instead of widening its column, with its
 * hint, when it has one, behind a small info icon. Shared by the rules and conflicts tables.
 */
defineProps<{
  label: string;
  hint?: string;
}>();
</script>

<template>
  <RuiTooltip
    :options="{ placement: 'top' }"
    :open-delay="400"
    :disabled="!hint"
    :class-names="{ tooltip: 'max-w-60' }"
  >
    <template #activator>
      <span class="inline-flex items-center gap-1.5 max-w-32 text-left whitespace-normal text-rui-text-secondary font-medium text-[0.8125rem] leading-4">
        {{ label }}
        <RuiIcon
          v-if="hint"
          class="shrink-0"
          size="14"
          name="lu-info"
        />
      </span>
    </template>
    {{ hint }}
  </RuiTooltip>
</template>
