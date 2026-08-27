<script setup lang="ts">
defineProps<{
  label: string;
  tooltip: string;
}>();
</script>

<template>
  <RuiTooltip
    :open-delay="200"
    :options="{ placement: 'top' }"
    tooltip-class="max-w-80"
  >
    <template #activator>
      <span
        class="inline-flex items-center gap-1 whitespace-nowrap rounded px-1.5 py-0.5 text-caption bg-rui-warning/10 text-rui-warning"
        data-testid="unmatched-untracked-badge"
      >
        <RuiIcon
          class="shrink-0"
          size="14"
          name="lu-triangle-alert"
        />
        {{ label }}
      </span>
    </template>
    {{ tooltip }}
  </RuiTooltip>
</template>
