import type { ComputedRef, Ref, WritableComputedRef } from 'vue';
import type { DialogState } from '@/modules/history/events/dialog-manager/types';
import type { AddTransactionHashPayload } from '@/modules/history/events/event-payloads';
import type { UnmatchedAssetMovement } from '@/modules/history/events/use-unmatched-asset-movements';
import type { UnmatchedBridgeTransaction } from '@/modules/history/events/use-unmatched-bridge-transactions';
import type {
  GroupEventData,
  HistoryEventEditData,
  StandaloneEventData,
} from '@/modules/history/management/forms/form-types';
import { startPromise } from '@shared/utils';
import { useHistoryEventsDialogManager } from '@/modules/history/events/dialog-manager/use-history-events-dialog-manager';
import { DIALOG_TYPES, type DialogShowOptions } from '@/modules/history/events/dialog-types';

interface PotentialMatchesState<T> {
  subject: Readonly<Ref<T | undefined>>;
  modelOpen: Ref<boolean>;
  open: (subject: T) => void;
  onMatched: () => void;
  onPinned: () => void;
}

export interface UseHistoryEventsDialogContainerOptions {
  /** Called once an asset movement has been matched. */
  onMovementMatched: () => void;
  /** Called once a bridge transaction has been matched. */
  onBridgeMatched: () => void;
}

export interface UseHistoryEventsDialogContainerReturn {
  /** Which dialog the manager currently has open. */
  currentDialog: Readonly<Ref<DialogState>>;
  /** Open a dialog through the manager. */
  show: (options: DialogShowOptions) => Promise<void>;
  /** Close whatever the manager has open. */
  closeDialog: () => void;
  /** `v-model` for the event form, which reads its data off the open dialog. */
  modelFormData: WritableComputedRef<GroupEventData | StandaloneEventData | undefined>;
  /** `v-model` for the missing rules dialog. */
  modelMissingRule: WritableComputedRef<HistoryEventEditData | undefined>;
  /** `v-model` for every dialog that is open purely because it is rendered. */
  modelDialogOpen: WritableComputedRef<boolean>;
  /** `v-model` for the add-transaction form, which the manager stores rather than the component. */
  modelAddTransaction: WritableComputedRef<AddTransactionHashPayload | undefined>;
  /** Whether the decoding status dialog refuses to close on a click outside. */
  decodingStatusPersistent: ComputedRef<boolean>;
  /** The movement whose potential matches are being shown, if any. */
  movementSubject: Readonly<Ref<UnmatchedAssetMovement | undefined>>;
  /** `v-model` for the movement potential-matches dialog. */
  modelMovementMatchesOpen: Ref<boolean>;
  /** Open the movement potential-matches dialog on a movement. */
  openMovementMatches: (movement: UnmatchedAssetMovement) => void;
  /** A movement was matched: drop it and tell the page to reload. */
  onMovementMatched: () => void;
  /** The movement list moved into the pinned rail: drop it and close the dialog behind it. */
  onMovementPinned: () => void;
  /** The bridge transaction whose potential matches are being shown, if any. */
  bridgeSubject: Readonly<Ref<UnmatchedBridgeTransaction | undefined>>;
  /** `v-model` for the bridge potential-matches dialog. */
  modelBridgeMatchesOpen: Ref<boolean>;
  /** Open the bridge potential-matches dialog on a transaction. */
  openBridgeMatches: (transaction: UnmatchedBridgeTransaction) => void;
  /** A bridge transaction was matched: drop it and tell the page to reload. */
  onBridgeMatched: () => void;
  /** The bridge list moved into the pinned rail: drop it and close the dialog behind it. */
  onBridgePinned: () => void;
}

/**
 * The models behind the dialog container.
 *
 * A manager-owned dialog is rendered by a `v-if` on the open dialog's type, so it is always "open"
 * while it exists and its `v-model` only has to answer a close; the data it edits is read back off
 * the manager's dialog state and narrowed here. The two potential-matches dialogs are opened by the
 * dialog above them rather than by the manager, so the container holds their state itself.
 */
export function useHistoryEventsDialogContainer(
  options: UseHistoryEventsDialogContainerOptions,
): UseHistoryEventsDialogContainerReturn {
  const { onBridgeMatched, onMovementMatched } = options;

  const { closeDialog, currentDialog, show } = useHistoryEventsDialogManager();

  const modelFormData = computed({
    get: () => {
      const dialog = get(currentDialog);
      return dialog.type === DIALOG_TYPES.EVENT_FORM ? dialog.data : undefined;
    },
    set: () => closeDialog(), // Dialog components handle their own closing
  });

  const modelMissingRule = computed({
    get: () => {
      const dialog = get(currentDialog);
      return dialog.type === DIALOG_TYPES.MISSING_RULES ? dialog.data : undefined;
    },
    set: () => closeDialog(),
  });

  const modelDialogOpen = computed({
    get: () => true, // Always true when dialog is rendered (due to v-if)
    set: () => closeDialog(),
  });

  const decodingStatusPersistent = computed<boolean>(() => {
    const dialog = get(currentDialog);
    return dialog.type === DIALOG_TYPES.DECODING_STATUS ? (dialog.data?.persistent ?? false) : false;
  });

  const modelAddTransaction = computed({
    get: () => {
      const dialog = get(currentDialog);
      return dialog.type === DIALOG_TYPES.TRANSACTION_FORM ? dialog.data : undefined;
    },
    set: (value: AddTransactionHashPayload | undefined) => {
      if (value) {
        startPromise(show({ data: value, type: DIALOG_TYPES.TRANSACTION_FORM }));
      }
      else {
        closeDialog();
      }
    },
  });

  /**
   * Builds the open state and subject of one potential-matches dialog.
   *
   * @remarks Its members have to be spread flat into the composable's return rather than passed
   * on as a nested object: a template only unwraps refs that are top-level setup bindings, so
   * `matches.modelOpen` would reach `v-model` as the ref itself.
   */
  function createPotentialMatches<T>(onMatched: () => void): PotentialMatchesState<T> {
    const subject = shallowRef<T>();
    const modelOpen = shallowRef<boolean>(false);

    return {
      modelOpen,
      onMatched: (): void => {
        set(subject, undefined);
        onMatched();
      },
      onPinned: (): void => {
        set(subject, undefined);
        closeDialog();
      },
      open: (target: T): void => {
        set(subject, target);
        set(modelOpen, true);
      },
      subject: shallowReadonly(subject),
    };
  }

  const movement = createPotentialMatches<UnmatchedAssetMovement>(onMovementMatched);
  const bridge = createPotentialMatches<UnmatchedBridgeTransaction>(onBridgeMatched);

  return {
    bridgeSubject: bridge.subject,
    closeDialog,
    currentDialog,
    decodingStatusPersistent,
    modelAddTransaction,
    modelBridgeMatchesOpen: bridge.modelOpen,
    modelDialogOpen,
    modelFormData,
    modelMissingRule,
    modelMovementMatchesOpen: movement.modelOpen,
    movementSubject: movement.subject,
    onBridgeMatched: bridge.onMatched,
    onBridgePinned: bridge.onPinned,
    onMovementMatched: movement.onMatched,
    onMovementPinned: movement.onPinned,
    openBridgeMatches: bridge.open,
    openMovementMatches: movement.open,
    show,
  };
}
