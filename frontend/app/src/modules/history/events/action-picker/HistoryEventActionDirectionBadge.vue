<script setup lang="ts">
import type { RuiIcons } from '@rotki/ui-library';

const { direction } = defineProps<{
  direction: 'in' | 'out' | 'neutral';
}>();

const { t } = useI18n({ useScope: 'global' });

const icon = computed<RuiIcons>(() => {
  switch (direction) {
    case 'in': return 'lu-arrow-left';
    case 'out': return 'lu-arrow-right';
    default: return 'lu-minus';
  }
});

const label = computed<string>(() => {
  switch (direction) {
    case 'in': return t('history_event_action.direction.in');
    case 'out': return t('history_event_action.direction.out');
    default: return t('history_event_action.direction.neutral');
  }
});

const colorClass = computed<string>(() => {
  switch (direction) {
    case 'in': return 'bg-rui-success/10 text-rui-success';
    case 'out': return 'bg-rui-error/10 text-rui-error';
    default: return 'bg-rui-grey-200 dark:bg-rui-grey-800 text-rui-text-secondary';
  }
});
</script>

<template>
  <span
    class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wide"
    :class="colorClass"
    :data-direction="direction"
  >
    <RuiIcon
      :name="icon"
      size="12"
    />
    {{ label }}
  </span>
</template>
