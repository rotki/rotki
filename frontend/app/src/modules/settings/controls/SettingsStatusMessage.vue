<script setup lang="ts">
const { error = '', success = '' } = defineProps<{
  error?: string;
  success?: string;
}>();

const CLEAR_DELAY_MS = 300;

const Status = {
  IDLE: 'idle',
  SUCCESS: 'success',
  ERROR: 'error',
} as const;

type Status = typeof Status[keyof typeof Status];

const displayedMessage = ref<string>('');
const displayedType = ref<Status>(Status.IDLE);

const { start: scheduleClear, stop: cancelClear } = useTimeoutFn(() => {
  set(displayedMessage, '');
  set(displayedType, Status.IDLE);
}, CLEAR_DELAY_MS, { immediate: false });

watchEffect(() => {
  if (error) {
    cancelClear();
    set(displayedMessage, error);
    set(displayedType, Status.ERROR);
  }
  else if (success) {
    cancelClear();
    set(displayedMessage, success);
    set(displayedType, Status.SUCCESS);
  }
  else if (get(displayedType) !== Status.IDLE) {
    scheduleClear();
  }
});
</script>

<template>
  <div
    class="min-h-[1.25rem] text-caption"
    :class="{
      'text-rui-success': displayedType === Status.SUCCESS,
      'text-rui-error': displayedType === Status.ERROR,
      'text-rui-text-secondary': displayedType === Status.IDLE,
    }"
    aria-live="polite"
  >
    {{ displayedMessage }}
  </div>
</template>
