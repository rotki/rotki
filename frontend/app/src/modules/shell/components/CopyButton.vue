<script setup lang="ts">
const { value, tooltip, size } = defineProps<{
  value: string;
  tooltip: string;
  size?: 'sm' | 'lg';
}>();

const { copy } = useClipboard({ source: () => value });
</script>

<template>
  <RuiTooltip
    :popper="{ placement: 'top', offsetDistance: 0 }"
    :open-delay="400"
  >
    <template #activator>
      <RuiButton
        :size="size"
        variant="text"
        icon
        @click="copy()"
      >
        <RuiIcon
          size="16"
          name="lu-copy"
        />
      </RuiButton>
    </template>
    <span>{{ tooltip }}</span>
  </RuiTooltip>
</template>
