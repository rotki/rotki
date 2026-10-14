<script setup lang="ts">
import HistoryEventsGroupToggle from '@/modules/history/events/components/HistoryEventsGroupToggle.vue';
import { injectHistoryEventsSelection } from '@/modules/history/events/use-history-events-selection-context';

const { canUnlink, eventCount, labelType, subgroupId } = defineProps<{
  /** Whether this matched subgroup can be unlinked from here; the parent decides. */
  canUnlink?: boolean;
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

const { isMdAndUp } = useBreakpoint();

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

    <RuiTooltip
      :open-delay="200"
      :disabled="isMdAndUp"
      class="shrink-0"
    >
      <template #activator>
        <RuiButton
          v-if="canUnlink"
          data-testid="collapse-unlink"
          class="h-6! [&>span]:hidden! md:[&>span]:inline!"
          variant="text"
          size="sm"
          color="warning"
          @click.stop="emit('unlink-event')"
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
