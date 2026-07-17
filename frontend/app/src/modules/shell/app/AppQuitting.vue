<script setup lang="ts">
const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div
    class="fixed inset-0 flex flex-col gap-4 justify-center items-center bg-rui-grey-50 dark:bg-rui-grey-900"
    data-testid="app-quitting"
  >
    <RuiProgress
      color="primary"
      variant="indeterminate"
      circular
      size="48"
    />
    <p class="mb-0 text-rui-text-secondary text-center">
      {{ t('app.quitting.message') }}
    </p>
  </div>
</template>
