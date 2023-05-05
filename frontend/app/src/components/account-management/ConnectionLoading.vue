<script setup lang="ts">
defineProps<{ connected: boolean }>();
const { t } = useI18n();
</script>

<template>
  <card v-if="!connected" flat>
    <v-row class="my-6">
      <v-col cols="auto" class="mx-2">
        <v-progress-circular color="primary" indeterminate />
      </v-col>
      <v-col class="grey-darken-1--text text-h5">
        <div class="ps-6">{{ t('connection_loading.message') }}</div>
      </v-col>
    </v-row>
  </card>
</template>
