<script setup lang="ts">
import type { HistoryEventBridgeUnlinkPayload, HistoryEventQuestion } from '@/modules/history/events/types';
import type { VirtualRow } from '@/modules/history/events/use-virtual-rows';
import { startPromise } from '@shared/utils';
import { injectHistoryEventsRowContext } from '@/modules/history/events/use-history-events-row-context';
import { type UnlinkKind, useUnlinkQuestion } from '@/modules/history/events/use-unlink-question';
import HistoryEventsDetailItem from './HistoryEventsDetailItem.vue';
import HistoryEventsGroupItem from './HistoryEventsGroupItem.vue';
import HistoryEventsLoadMoreRow from './HistoryEventsLoadMoreRow.vue';
import HistoryEventsMatchedMovementItem from './HistoryEventsMatchedMovementItem.vue';
import HistoryEventsRowPlaceholder from './HistoryEventsRowPlaceholder.vue';
import HistoryEventsSwapCollapseRow from './HistoryEventsSwapCollapseRow.vue';
import HistoryEventsSwapItem from './HistoryEventsSwapItem.vue';

defineProps<{
  row: VirtualRow;
}>();

const { actions, display, highlight, lookups } = injectHistoryEventsRowContext();

// Lifted to the top level so the template unwraps them; a ref nested in an object does not.
const { duplicateHandlingStatus, eventsLoading, hideActions, variant } = display;

const { unlinkQuestion } = useUnlinkQuestion();

function unlinkBridge(payload?: HistoryEventBridgeUnlinkPayload): void {
  if (payload)
    startPromise(actions.unlinkEvent(payload));
}

/** What a collapsed match's header asks before it unlinks; nothing, when it cannot unlink. */
function collapseUnlinkConfirm(kind: UnlinkKind | undefined): HistoryEventQuestion | undefined {
  return kind && !get(hideActions) ? unlinkQuestion(kind) : undefined;
}
</script>

<template>
  <HistoryEventsGroupItem
    v-if="row.type === 'group-header'"
    :group="row.data"
    :group-events="lookups.groupEvents(row.groupId)"
    :hide-actions="hideActions"
    :loading="eventsLoading"
    :duplicate-handling-status="duplicateHandlingStatus"
    :ignored-assets="lookups.ignoredAssets(row.groupId)"
    :highlight-type="highlight.isGroupHighlighted(row.groupId) ? highlight.getHighlightType(row.data) : undefined"
    :variant="variant"
    @add-event="actions.addEvent($event, row.data)"
    @toggle-ignore="actions.toggleIgnore($event)"
    @toggle-show-ignored-assets="actions.toggleShowIgnoredAssets(row.groupId)"
    @redecode="actions.redecode($event, row.data.groupIdentifier)"
    @redecode-with-options="actions.redecodeWithOptions($event, row.data.groupIdentifier)"
    @delete-tx="actions.deleteTransaction($event)"
    @delete-events="actions.deleteEvents({ type: 'delete', ids: $event })"
    @fix-duplicate="actions.refresh()"
    @ignore-duplicate="actions.refresh()"
  />

  <HistoryEventsRowPlaceholder
    v-else-if="row.type === 'event-placeholder'"
    :variant="variant"
  />

  <HistoryEventsDetailItem
    v-else-if="row.type === 'event-row'"
    :event="row.data"
    :index="row.index"
    :complete-group-events="lookups.completeEventsForItem(row.groupId, row.data)"
    :group-location-label="lookups.groupLocationLabel(row.groupId)"
    :linked-leg="row.linkedLeg"
    :hide-actions="hideActions"
    :highlight-type="highlight.isHighlighted(row.data) ? highlight.getHighlightType(row.data) : undefined"
    :variant="variant"
    @edit-event="actions.editEvent($event, row.groupId)"
    @delete-event="actions.deleteEvents($event)"
    @show:missing-rule-action="actions.addMissingRule($event, row.groupId)"
    @refresh="actions.refresh()"
  />

  <HistoryEventsSwapItem
    v-else-if="row.type === 'swap-row'"
    :events="row.events"
    :complete-group-events="lookups.completeSubgroupEvents(row.events)"
    :group-location-label="lookups.groupLocationLabel(row.groupId)"
    :hide-actions="hideActions"
    :highlight="highlight.isSwapHighlighted(row.events)"
    :highlight-type="highlight.getSwapHighlightType(row.events)"
    :variant="variant"
    @edit-event="actions.editEvent($event, row.groupId)"
    @delete-event="actions.deleteEvents($event)"
    @show:missing-rule-action="actions.addMissingRule($event, row.groupId)"
    @unlink-event="actions.unlinkEvent($event)"
    @refresh="actions.refresh()"
    @toggle-expand="actions.toggleSwapExpanded(row.swapKey)"
  />

  <HistoryEventsSwapCollapseRow
    v-else-if="row.type === 'swap-collapse'"
    :event-count="row.eventCount"
    :subgroup-id="row.subgroupId"
    :label-type="row.bridge ? 'bridge' : undefined"
    :unlink-confirm="collapseUnlinkConfirm(row.bridgeUnlink)"
    @unlink-event="unlinkBridge(row.bridgeUnlink)"
    @collapse="actions.toggleSwapExpanded(row.swapKey)"
  />

  <HistoryEventsMatchedMovementItem
    v-else-if="row.type === 'matched-movement-row'"
    :events="row.events"
    :complete-group-events="lookups.completeSubgroupEvents(row.events)"
    :group-location-label="lookups.groupLocationLabel(row.groupId)"
    :hide-actions="hideActions"
    :highlight="highlight.isSwapHighlighted(row.events)"
    :highlight-type="highlight.getSwapHighlightType(row.events)"
    :variant="variant"
    @edit-event="actions.editEvent($event, row.groupId)"
    @delete-event="actions.deleteEvents($event)"
    @show:missing-rule-action="actions.addMissingRule($event, row.groupId)"
    @unlink-event="actions.unlinkEvent($event)"
    @refresh="actions.refresh()"
    @toggle-expand="actions.toggleMovementExpanded(row.movementKey)"
  />

  <HistoryEventsSwapCollapseRow
    v-else-if="row.type === 'matched-movement-collapse'"
    :event-count="row.eventCount"
    label-type="movement"
    :unlink-confirm="collapseUnlinkConfirm({ type: 'asset-movement' })"
    @unlink-event="actions.unlinkGroup(row.groupId)"
    @collapse="actions.toggleMovementExpanded(row.movementKey)"
  />

  <HistoryEventsLoadMoreRow
    v-else-if="row.type === 'load-more'"
    :hidden-count="row.hiddenCount"
    @load-more="actions.loadMore(row.groupId)"
  />
</template>
