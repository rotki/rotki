<script setup lang="ts">
import { isRetryableFailure } from '@/modules/core/api/request-result';
import { useFailureMessage } from '@/modules/core/api/use-failure-message';

/**
 * One line saying a load or a save failed, above the content it concerns.
 *
 * @remarks
 * The content stays usable, so this stays quiet: a tinted, bordered line rather than an alert box.
 * Pass `in-table` for a row above a table's own rows, where the table supplies the frame. Retry
 * shows only when the caller binds `@retry` and the failure's cause leaves a retry worth offering: a
 * failed save leaves it off, since its own button is the retry. `failure` is worded by
 * `useFailureMessage`, so a caller passes the error itself, or a string already worded, which names
 * no cause. The optional `action` slot holds one more thing the user can do about the failure, such
 * as a link to read more, shown beside the message and before retry.
 */
const { failure, inTable = false, onRetry } = defineProps<{
  title: string;
  failure: unknown;
  inTable?: boolean;
  /** Bound through `@retry`; declared as a prop so the strip can tell whether anyone listens. */
  onRetry?: () => void;
}>();

defineSlots<{
  action?: () => any;
}>();

const { t } = useI18n({ useScope: 'global' });

const failureMessage = useFailureMessage();

const canRetry = computed<boolean>(() => !!onRetry && isRetryableFailure(failure));
</script>

<template>
  <div
    class="flex items-start gap-2 px-4 py-2 text-body-2 bg-rui-error/10 text-rui-error"
    :class="inTable ? 'border-b border-rui-error/30' : 'rounded-md border border-rui-error/30'"
    role="alert"
    data-testid="failure-strip"
  >
    <RuiIcon
      name="lu-circle-alert"
      size="16"
      class="shrink-0 mt-0.5"
    />
    <span class="flex-1 min-w-0 whitespace-normal">
      <span class="font-medium">{{ title }}:</span>
      {{ failureMessage(failure) }}
    </span>
    <slot name="action" />
    <button
      v-if="canRetry"
      type="button"
      class="shrink-0 underline underline-offset-2 hover:no-underline"
      data-testid="failure-strip-retry"
      @click="onRetry?.()"
    >
      {{ t('common.actions.retry') }}
    </button>
  </div>
</template>
