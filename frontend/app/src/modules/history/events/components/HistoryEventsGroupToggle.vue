<script setup lang="ts">
const { count, expanded = false, selecting = false } = defineProps<{
  count: number;
  expanded?: boolean;
  /** Selection mode widens the row gutter for the checkboxes, so the toggle moves past them. */
  selecting?: boolean;
}>();

const emit = defineEmits<{
  toggle: [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RuiButton
    variant="text"
    icon
    size="sm"
    class="absolute z-1 top-1.5 size-6! rounded-full! text-rui-primary bg-rui-primary/10 hover:bg-rui-primary/20"
    :class="selecting ? 'left-11' : 'left-3'"
    :aria-expanded="expanded"
    :aria-label="expanded ? t('history_events_list_swap.collapse_events', { count }) : t('history_events_list_swap.expand_events', { count })"
    @click.stop="emit('toggle')"
  >
    <RuiIcon
      :name="expanded ? 'lu-chevron-up' : 'lu-chevron-down'"
      size="14"
    />
  </RuiButton>
</template>
