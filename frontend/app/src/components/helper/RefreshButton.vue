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
      <VBtn
        fab
        text
        small
        depressed
        :disabled="loading || disabled"
        v-bind="attrs"
        @click="refresh()"
        v-on="on"
      >
        <VProgressCircular
          v-if="loading"
          rounded
          indeterminate
          size="20"
          width="2"
          color="primary"
        />
        <VIcon v-else color="primary">mdi-refresh</VIcon>
      </VBtn>
    </template>
    <span>{{ tooltip }}</span>
  </VTooltip>
</template>
