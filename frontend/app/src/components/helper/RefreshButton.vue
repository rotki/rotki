<script setup lang="ts">
withDefaults(
  defineProps<{
    loading?: boolean;
    tooltip: string;
    disabled?: boolean;
  }>(),
  {
    disabled: false,
    loading: false,
  },
);

const emit = defineEmits<{
  refresh: [];
}>();
</script>

<template>
  <RuiTooltip
    :popper="{ placement: 'top' }"
    :open-delay="400"
  >
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
        <RuiIcon name="lu-refresh-ccw" />
      </RuiButton>
    </template>
    {{ tooltip }}
  </RuiTooltip>
</template>
