<script setup lang="ts">
defineProps<{ remoteVersion: number }>();

const emit = defineEmits<{ (e: 'confirm'): void }>();

const { t } = useI18n();
</script>

<template>
  <Card flat :outlined="false">
    <template #title>
      {{ t('asset_update.success.title') }}
    </template>

    <VRow class="mt-2 text-body-1">
      <VCol cols="auto" class="mx-2">
        <VIcon x-large color="success">mdi-check-circle</VIcon>
      </VCol>
      <VCol>
        {{ t('asset_update.success.description', { remoteVersion }) }}
      </VCol>
    </VRow>

    <template #buttons>
      <VSpacer />
      <VBtn color="primary" depressed @click="emit('confirm')">
        {{ t('asset_update.success.ok') }}
      </VBtn>
    </template>
  </Card>
</template>
