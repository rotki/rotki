<script setup lang="ts">
defineProps<{ connected: boolean }>();
const { t } = useI18n();
</script>

<template>
  <Card v-if="!connected" flat :outlined="false">
    <VRow class="my-6">
      <VCol cols="auto" class="mx-2">
        <VProgressCircular color="primary" indeterminate />
      </VCol>
      <VCol class="grey-darken-1--text text-h5">
        <div class="ps-6">{{ t('connection_loading.message') }}</div>
      </VCol>
    </VRow>
  </Card>
</template>
