<script setup lang="ts">
// Marks a bridge leg whose counterpart address rotki does not track, so no counterpart event
// can ever be decoded for it. The wording arrives from the row - see use-unmatched-bridge-rows.
defineProps<{
  label: string;
  tooltip: string;
}>();
</script>

<template>
  <RuiTooltip
    :open-delay="200"
    :popper="{ placement: 'top' }"
    tooltip-class="max-w-80"
  >
    <template #activator>
      <RuiChip
        size="sm"
        color="warning"
        class="!py-0"
      >
        <span class="flex items-center gap-1">
          <RuiIcon
            size="14"
            name="lu-triangle-alert"
          />
          {{ label }}
        </span>
      </RuiChip>
    </template>
    {{ tooltip }}
  </RuiTooltip>
</template>
