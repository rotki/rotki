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
  <v-tooltip top>
    <template #activator="{ on, attrs }">
      <v-btn
        fab
        text
        small
        depressed
        :disabled="loading || disabled"
        v-bind="attrs"
        @click="refresh()"
        v-on="on"
      >
        <v-progress-circular
          v-if="loading"
          rounded
          indeterminate
          size="20"
          width="2"
          color="primary"
        />
        <v-icon v-else color="primary">mdi-refresh</v-icon>
      </v-btn>
    </template>
    <span>{{ tooltip }}</span>
  </v-tooltip>
</template>
