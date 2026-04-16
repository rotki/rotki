<script setup lang="ts">
defineProps<{ connected: boolean }>();
const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RuiCard
    v-if="!connected"
    variant="flat"
    class="max-w-[27.5rem] mx-auto !bg-transparent"
  >
    <div class="flex items-center space-x-10">
      <RuiProgress
        color="primary"
        variant="indeterminate"
        circular
      />
      <h5
        class="text-rui-text-secondary text-h5"
        data-cy="connection-loading__content"
      >
        {{ t('connection_loading.message') }}
      </h5>
    </div>
  </RuiCard>
</template>
