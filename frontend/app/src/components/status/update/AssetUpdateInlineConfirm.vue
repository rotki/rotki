<script setup lang="ts">
defineProps<{ remoteVersion: number }>();

const emit = defineEmits<{ (e: 'confirm'): void }>();

const { t } = useI18n();
</script>

<template>
  <card flat>
    <template #title>
      {{ t('asset_update.success.title') }}
    </template>

    <v-row class="mt-2 text-body-1">
      <v-col cols="auto" class="mx-2">
        <v-icon x-large color="success">mdi-check-circle</v-icon>
      </v-col>
      <v-col>
        {{ t('asset_update.success.description', { remoteVersion }) }}
      </v-col>
    </v-row>

    <template #buttons>
      <v-spacer />
      <v-btn color="primary" depressed @click="emit('confirm')">
        {{ t('asset_update.success.ok') }}
      </v-btn>
    </template>
  </card>
</template>
