<script setup lang="ts">
/**
 * One line saying a refresh failed, for above the rows an earlier load left.
 *
 * @remarks
 * The rows stay usable, so this stays quiet: a tinted line inside the table rather than an alert box.
 * Pass `standalone` where it sits outside a table and needs its own border.
 */
const { standalone = false } = defineProps<{
  title: string;
  message: string;
  standalone?: boolean;
}>();

const emit = defineEmits<{
  retry: [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div
    class="flex items-start gap-2 px-4 py-2 text-body-2 bg-rui-error/10 text-rui-error"
    :class="standalone ? 'rounded-md border border-rui-error/30' : 'border-b border-rui-error/30'"
    role="alert"
    data-testid="table-failure-strip"
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
      type="button"
      class="shrink-0 underline underline-offset-2 hover:no-underline"
      data-testid="table-failure-strip-retry"
      @click="emit('retry')"
    >
      {{ t('common.actions.retry') }}
    </button>
  </div>
</template>
