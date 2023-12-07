<script setup lang="ts">
withDefaults(
  defineProps<{
    loading?: boolean;
    tooltip: string;
    disabled?: boolean;
  }>(),
  {
    disabled: false,
    loading: false
  }
);

const emit = defineEmits<{
  (e: 'refresh'): void;
}>();
</script>

<template>
  <RuiTooltip :popper="{ placement: 'top' }" :open-delay="400">
    <template #activator>
      <RuiButton
        icon
        size="sm"
        variant="text"
        :disabled="loading || disabled"
        :loading="loading"
        color="primary"
        @click="emit('refresh')"
      >
        <RuiIcon name="refresh-line" />
      </RuiButton>
    </template>
    <span>{{ tooltip }}</span>
  </RuiTooltip>
</template>
