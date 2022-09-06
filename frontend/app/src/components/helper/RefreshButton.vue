<template>
  <v-tooltip top>
    <template #activator="{ on, attrs }">
      <v-btn
        fab
        text
        small
        depressed
        :disabled="loading"
        v-bind="attrs"
        @click="refresh"
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
<script setup lang="ts">
defineProps({
  loading: { required: true, type: Boolean },
  tooltip: { required: true, type: String }
});

const emit = defineEmits(['refresh']);

const refresh = () => {
  emit('refresh');
};
</script>
