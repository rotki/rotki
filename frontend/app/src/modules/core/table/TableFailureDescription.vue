<script setup lang="ts">
import { isRetryableFailure } from '@/modules/core/api/request-result';

/**
 * The reason a load failed and a retry, for the description slot of an empty state that names the
 * failure.
 *
 * @remarks
 * `failure` is the failure itself, which decides whether a retry is offered. `message` stays apart
 * because a caller words it: an empty state's text, or a reason already worded.
 */
const { failure, message } = defineProps<{
  message: string;
  failure: unknown;
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
      v-if="isRetryableFailure(failure)"
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
