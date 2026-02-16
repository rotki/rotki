<script setup lang="ts">
import type { HistoryEventEntry } from '@/types/history/events/schemas';

const props = defineProps<{
  eventCount: number;
  labelType?: 'swap' | 'movement';
  events?: HistoryEventEntry[];
}>();

const emit = defineEmits<{
  'collapse': [];
  'unlink-event': [];
}>();

const { t } = useI18n({ useScope: 'global' });

const isMovement = computed<boolean>(() => props.labelType === 'movement');

const { isMdAndUp } = useBreakpoint();
</script>

<template>
  <div
    class="h-9 flex items-center gap-2 border-default pr-4 pl-2 bg-gradient-to-b from-rui-grey-300 to-transparent dark:from-rui-grey-900 group/row relative mx-2 rounded-t-2xl mt-[3px]"
  >
    <!-- Collapse button (absolute top-left like expand) -->
    <RuiButton
      size="sm"
      icon
      color="primary"
      class="size-5 z-[6]"
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

    <RuiTooltip
      :open-delay="200"
      :disabled="isMdAndUp"
      class="ml-auto"
    >
      <template #activator>
        <RuiButton
          v-if="isMovement"
          class="!h-6 [&>span]:!hidden md:[&>span]:!inline"
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
      </template>
      {{ t('transactions.events.actions.unlink') }}
    </RuiTooltip>
  </div>
</template>
