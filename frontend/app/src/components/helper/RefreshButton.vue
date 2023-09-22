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

const refresh = () => {
  emit('refresh');
};
</script>

<template>
  <VTooltip top>
    <template #activator="{ on, attrs }">
      <RuiButton
        size="sm"
        :disabled="loading || disabled"
        variant="text"
        v-bind="attrs"
        color="primary"
        @click="refresh()"
        v-on="on"
      >
        <VProgressCircular
          v-if="loading"
          rounded
          indeterminate
          size="20"
          width="2"
        />
        <RuiIcon v-else name="restart-line" />
      </RuiButton>
    </template>
    <span>{{ tooltip }}</span>
  </VTooltip>
</template>
