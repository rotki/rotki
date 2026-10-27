<script setup lang="ts">
/**
 * One line saying a load or a save failed, above the content it concerns.
 *
 * @remarks
 * The content stays usable, so this stays quiet: a tinted, bordered line rather than an alert box.
 * Pass `in-table` for a row above a table's own rows, where the table supplies the frame, and
 * `retryable: false` for a failed save, whose own button is the retry.
 */
const { inTable = false, retryable = true } = defineProps<{
  title: string;
  message: string;
  inTable?: boolean;
  retryable?: boolean;
}>();

const emit = defineEmits<{
  retry: [];
}>();

const { t } = useI18n({ useScope: 'global' });
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
      {{ message }}
    </span>
    <button
      v-if="retryable"
      type="button"
      class="shrink-0 underline underline-offset-2 hover:no-underline"
      data-testid="failure-strip-retry"
      @click="emit('retry')"
    >
      {{ t('common.actions.retry') }}
    </button>
  </div>
</template>
