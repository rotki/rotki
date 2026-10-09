<script setup lang="ts">
const { connected, loggingIn = false, restarting = false } = defineProps<{
  connected: boolean;
  restarting?: boolean;
  loggingIn?: boolean;
}>();
const { t } = useI18n({ useScope: 'global' });

const message = computed<string>(() => {
  if (restarting)
    return t('connection_loading.restarting');
  if (loggingIn)
    return t('connection_loading.logging_in');
  return t('connection_loading.message');
});
</script>

<template>
  <!-- grows into the page's column, so the wait sits mid-screen whatever the form's alignment -->
  <div
    v-if="!connected"
    class="grow w-full max-w-110 mx-auto flex flex-col gap-4 justify-center items-center py-12"
  >
    <RuiProgress
      color="primary"
      variant="indeterminate"
      circular
      size="48"
    />
    <p
      class="mb-0 text-rui-text-secondary text-center"
      data-testid="connection-loading-content"
    >
      {{ message }}
    </p>
  </div>
</template>
