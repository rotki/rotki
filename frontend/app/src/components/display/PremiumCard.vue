<script setup lang="ts">
defineProps({
  title: {
    required: true,
    type: String
  }
});
</script>

<template>
  <v-card>
    <v-card-title>
      {{ title }}
      <v-spacer />
      <premium-lock />
    </v-card-title>
  </v-card>
</template>
