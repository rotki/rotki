<script setup lang="ts">
const { connected, restarting = false } = defineProps<{
  connected: boolean;
  restarting?: boolean;
}>();
const { t } = useI18n({ useScope: 'global' });

const message = computed<string>(() =>
  restarting ? t('connection_loading.restarting') : t('connection_loading.message'),
);
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
        {{ message }}
      </h5>
    </div>
  </RuiCard>
</template>
