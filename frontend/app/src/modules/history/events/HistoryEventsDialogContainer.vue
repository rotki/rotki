<script setup lang="ts">
import type { DialogEventHandlers } from '@/modules/history/events/dialog-types';
import type { AccountingRuleEntry } from '@/modules/settings/types/accounting';
import {
  AccountingRuleFormDialog,
  BridgePotentialMatchesDialog,
  CustomizedEventDuplicatesDialog,
  HistoryEventFormDialog,
  HistoryEventsDecodingStatusDialog,
  HistoryEventsProtocolCacheStatusDialog,
  InternalTxConflictsDialog,
  MatchAssetMovementsDialog,
  MatchBridgeTransactionsDialog,
  MissingRulesDialog,
  PotentialMatchesDialog,
  RepullingTransactionFormDialog,
  TransactionFormDialog,
} from '@/modules/history/events/dialog-components';
import { useHistoryEventsDialogContainer } from '@/modules/history/events/use-history-events-dialog-container';
import { DIALOG_TYPES } from './dialog-types';

const accountingRuleToEdit = defineModel<AccountingRuleEntry | undefined>('accountingRuleToEdit', { required: true });

const { eventHandlers, selectedEventIds } = defineProps<{
  eventHandlers: DialogEventHandlers;
  loading?: boolean;
  refreshing?: boolean;
  sectionLoading?: boolean;
  selectedEventIds: number[];
}>();

const emit = defineEmits<{
  'accounting-rule-refresh': [];
  'bridge-matched': [];
  'movement-matched': [];
}>();

const {
  bridgeSubject,
  closeDialog,
  currentDialog,
  decodingStatusPersistent,
  modelAddTransaction,
  modelBridgeMatchesOpen,
  modelDialogOpen,
  modelFormData,
  modelMissingRule,
  modelMovementMatchesOpen,
  movementSubject,
  onBridgeMatched,
  onBridgePinned,
  onMovementMatched,
  onMovementPinned,
  openBridgeMatches,
  openMovementMatches,
  show,
} = useHistoryEventsDialogContainer({
  onBridgeMatched: () => emit('bridge-matched'),
  onMovementMatched: () => emit('movement-matched'),
});

defineExpose({
  show,
  showBridgePotentialMatches: openBridgeMatches,
  showPotentialMatches: openMovementMatches,
});
</script>

<template>
  <div class="history-events-dialog-container">
    <HistoryEventFormDialog
      v-if="currentDialog.type === DIALOG_TYPES.EVENT_FORM"
      v-model="modelFormData"
      :loading="loading"
      @refresh="eventHandlers.onHistoryEventSaved?.()"
    />

    <TransactionFormDialog
      v-if="currentDialog.type === DIALOG_TYPES.TRANSACTION_FORM"
      v-model="modelAddTransaction"
      :loading="sectionLoading"
      @reload="eventHandlers.onTransactionAdded?.($event)"
    />

    <RepullingTransactionFormDialog
      v-if="currentDialog.type === DIALOG_TYPES.REPULLING_TRANSACTION"
      v-model="modelDialogOpen"
      :loading="sectionLoading"
      :repull-transactions="eventHandlers.onRepullTransactions"
      :repull-exchange-events="eventHandlers.onRepullExchangeEvents"
    />

    <MissingRulesDialog
      v-if="currentDialog.type === DIALOG_TYPES.MISSING_RULES"
      v-model="modelMissingRule"
      @edit-event="show({ data: $event, type: DIALOG_TYPES.EVENT_FORM })"
      @redecode="eventHandlers.onRedecodeTransaction?.($event)"
      @add="show({ data: $event, type: DIALOG_TYPES.ADD_MISSING_RULE })"
      @dismiss="closeDialog()"
    />

    <HistoryEventsDecodingStatusDialog
      v-if="currentDialog.type === DIALOG_TYPES.DECODING_STATUS"
      v-model="modelDialogOpen"
      :refreshing="refreshing"
      :persistent="decodingStatusPersistent"
      @redecode-all-events="eventHandlers.onRedecodeAllEvents?.()"
      @reset-undecoded-transactions="eventHandlers.onResetUndecodedTransactions?.()"
    />

    <HistoryEventsProtocolCacheStatusDialog
      v-if="currentDialog.type === DIALOG_TYPES.PROTOCOL_CACHE"
      v-model="modelDialogOpen"
      :refreshing="refreshing"
    />

    <AccountingRuleFormDialog
      v-model="accountingRuleToEdit"
      :event-ids="selectedEventIds"
      @refresh="emit('accounting-rule-refresh')"
    />

    <CustomizedEventDuplicatesDialog
      v-if="currentDialog.type === DIALOG_TYPES.CUSTOMIZED_EVENT_DUPLICATES"
      v-model="modelDialogOpen"
    />

    <InternalTxConflictsDialog
      v-if="currentDialog.type === DIALOG_TYPES.INTERNAL_TX_CONFLICTS"
      v-model="modelDialogOpen"
    />

    <MatchAssetMovementsDialog
      v-if="currentDialog.type === DIALOG_TYPES.MATCH_ASSET_MOVEMENTS"
      v-model="modelDialogOpen"
      @refresh="eventHandlers.onHistoryEventSaved?.()"
      @find-match="openMovementMatches($event)"
    />

    <PotentialMatchesDialog
      v-if="movementSubject && modelMovementMatchesOpen"
      v-model="modelMovementMatchesOpen"
      :movement="movementSubject"
      @matched="onMovementMatched()"
      @pinned="onMovementPinned()"
    />

    <MatchBridgeTransactionsDialog
      v-if="currentDialog.type === DIALOG_TYPES.MATCH_BRIDGE_TRANSACTIONS"
      v-model="modelDialogOpen"
      @find-match="openBridgeMatches($event)"
    />

    <BridgePotentialMatchesDialog
      v-if="bridgeSubject && modelBridgeMatchesOpen"
      v-model="modelBridgeMatchesOpen"
      :transaction="bridgeSubject"
      @matched="onBridgeMatched()"
      @pinned="onBridgePinned()"
    />
  </div>
</template>
