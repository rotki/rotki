<script setup lang="ts">
/** The reason a load failed and a retry, for the description slot of an empty state that names the failure. */
defineProps<{
  message: string;
}>();

const emit = defineEmits<{
  retry: [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="flex flex-col items-center gap-3">
    <p
      class="text-body-2 text-center text-rui-text-secondary whitespace-normal max-w-md mb-0"
      data-testid="table-failure-message"
    >
      {{ message }}
    </p>
    <RuiButton
      variant="outlined"
      color="primary"
      size="sm"
      data-testid="table-failure-retry"
      @click="emit('retry')"
    >
      <template #prepend>
        <RuiIcon
          name="lu-refresh-cw"
          size="14"
        />
      </template>
      {{ t('common.actions.retry') }}
    </RuiButton>
  </div>
</template>
