<script setup lang="ts">
defineProps<{
  count: number;
}>();

const emit = defineEmits<{
  expand: [];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RuiButton
    variant="text"
    size="sm"
    class="h-6! px-1.5! text-xs text-rui-text-secondary shrink-0"
    aria-expanded="false"
    @click.stop="emit('expand')"
  >
    {{ t('history_events_list_swap.event_count', { count }) }}
    <template #append>
      <RuiIcon
        name="lu-chevron-down"
        size="14"
      />
    </template>
  </RuiButton>
</template>
