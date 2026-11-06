<script setup lang="ts">
import type { HistoryEventQuestion } from '@/modules/history/events/types';
import HistoryEventsGroupToggle from '@/modules/history/events/components/HistoryEventsGroupToggle.vue';
import HistoryEventsUnlinkButton from '@/modules/history/events/components/HistoryEventsUnlinkButton.vue';
import { injectHistoryEventsSelection } from '@/modules/history/events/use-history-events-selection-context';

const { unlinkConfirm, eventCount, labelType, subgroupId } = defineProps<{
  /**
   * Offers unlink on this matched subgroup, asking this beside the button before `unlink-event` is
   * emitted. The parent decides whether the subgroup can be unlinked from here.
   */
  unlinkConfirm?: HistoryEventQuestion;
  eventCount: number;
  labelType?: 'swap' | 'movement' | 'bridge';
  /**
   * Identity of the subgroup this header stands for, mirrored onto the collapsed row.
   * A swap that merely changes expansion keeps the same id, so a test asserting the id is gone
   * cannot mistake a re-render for a deletion.
   */
  subgroupId?: number;
}>();

const emit = defineEmits<{
  'collapse': [];
  'unlink-event': [];
}>();

const { t } = useI18n({ useScope: 'global' });

const selection = injectHistoryEventsSelection();

/** Selection mode widens the rows' gutter, so the toggle and label move with the row they head. */
const selecting = computed<boolean>(() => !!selection && get(selection.isSelectionMode));

const isMovement = computed<boolean>(() => labelType === 'movement');

const label = computed<string>(() => {
  if (labelType === 'movement')
    return t('history_events_list_swap.movement_expanded', { count: eventCount });
  if (labelType === 'bridge')
    return t('history_events_list_swap.bridge_expanded', { count: eventCount });
  return t('history_events_list_swap.swap_expanded', { count: eventCount });
});
</script>

<template>
  <div
    :data-testid="isMovement ? 'movement-collapse' : 'swap-collapse'"
    :data-event-id="subgroupId"
    class="h-9 flex items-center gap-2 pr-4 relative border-b border-default cursor-pointer bg-rui-primary/5 hover:bg-rui-primary/10 transition-colors"
    @click="emit('collapse')"
  >
    <HistoryEventsGroupToggle
      data-testid="collapse-toggle"
      :count="eventCount"
      :selecting="selecting"
      expanded
      @toggle="emit('collapse')"
    />

    <span
      class="flex-1 min-w-0 truncate text-sm font-medium text-rui-text-secondary"
      :class="selecting ? 'pl-19' : 'pl-11'"
    >
      {{ label }}
    </span>

    <HistoryEventsUnlinkButton
      v-if="unlinkConfirm"
      :question="unlinkConfirm"
      @confirm="emit('unlink-event')"
    />
  </div>
</template>
