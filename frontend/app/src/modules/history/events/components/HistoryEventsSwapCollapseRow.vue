<script setup lang="ts">
const props = defineProps<{
  eventCount: number;
  labelType?: 'swap' | 'movement';
}>();

const emit = defineEmits<{
  'collapse': [];
  'unlink-event': [];
}>();

const { t } = useI18n({ useScope: 'global' });

const isMovement = computed<boolean>(() => props.labelType === 'movement');
</script>

<template>
  <div class="h-9 flex items-center gap-2 border-b border-default px-4 pl-8 bg-rui-grey-50 dark:bg-rui-grey-900 group/row relative">
    <!-- Collapse button (absolute top-left like expand) -->
    <RuiButton
      size="sm"
      icon
      color="primary"
      class="size-5 absolute top-1.5 left-2 z-[6]"
      @click="emit('collapse')"
    >
      <RuiIcon
        class="hidden group-hover/row:block"
        name="lu-fold-vertical"
        size="14"
      />
      <span class="group-hover/row:hidden text-xs">{{ eventCount }}</span>
    </RuiButton>

    <!-- Label -->
    <span class="text-xs text-rui-text-secondary">
      {{
        isMovement
          ? t('history_events_list_swap.movement_expanded', { count: eventCount })
          : t('history_events_list_swap.swap_expanded', { count: eventCount })
      }}
    </span>
    <RuiButton
      v-if="isMovement"
      class="ml-auto"
      variant="text"
      size="sm"
      color="warning"
      @click="emit('unlink-event')"
    >
      <template #prepend>
        <RuiIcon
          name="lu-unlink"
          size="14"
        />
      </template>
      {{ t('transactions.events.actions.unlink') }}
    </RuiButton>
  </div>
</template>
