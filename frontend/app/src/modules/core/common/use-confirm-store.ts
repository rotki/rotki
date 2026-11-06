import type { DialogType } from '@/modules/core/common/dialogs';

export interface ConfirmationMessage {
  title: string;
  message: string;
  type?: DialogType;
  /** An acknowledgement with only the primary button; Escape acknowledges it too. */
  singleAction?: boolean;
  primaryAction?: string;
  /** Label of the button that backs out, which Escape does too; defaults to "Cancel". */
  secondaryAction?: string;
  /** Label of a third button for a different outcome than confirming, shown only when set. */
  alternativeAction?: string;
}

/** Which way a confirmation was answered. */
export type ConfirmChoice = 'confirm' | 'dismiss' | 'alternative';

function defaultMessage(): ConfirmationMessage {
  return {
    message: '',
    singleAction: false,
    title: '',
    type: 'warning',
  };
}

/**
 * The app-wide confirmation dialog, for the few questions with nowhere better to be asked: bulk
 * deletes with more than two outcomes, a route guard, and prompts raised after the action that
 * caused them has finished.
 *
 * @remarks
 * State only: callers ask through `useConfirm`, whose `ask` wraps `open` in a promise. `open` hands
 * every way out to its callback, so a caller awaiting the answer cannot hang on a cancel. The dialog
 * calls `confirm`, `dismiss` and `alternative` to answer it.
 */
export const useConfirmStore = defineStore('confirm', () => {
  const visible = ref<boolean>(false);
  const confirmation = ref<ConfirmationMessage>(defaultMessage());

  /** Answers the latest question; replaced by a no-op once it is answered, so it answers once. */
  let settle: (choice: ConfirmChoice) => void = () => {};

  const { start, stop } = useTimeoutFn(
    () => {
      set(confirmation, defaultMessage());
    },
    3000,
    { immediate: false },
  );

  function answer(choice: ConfirmChoice): void {
    set(visible, false);
    start();
    const pending = settle;
    settle = (): void => {};
    pending(choice);
  }

  const confirm = (): void => answer('confirm');

  /** Backing out, by the button or by Escape. An acknowledgement with one button counts as confirmed. */
  const dismiss = (): void => answer(get(confirmation).singleAction ? 'confirm' : 'dismiss');

  const alternative = (): void => answer('alternative');

  /**
   * Shows the confirmation, and calls `onAnswer` once with how it was answered.
   *
   * @remarks
   * The alternative is only offered when `message.alternativeAction` is set. A question still on
   * screen when another is opened is answered as dismissed, so it never leaves its caller waiting.
   */
  function open(message: ConfirmationMessage, onAnswer: (choice: ConfirmChoice) => void): void {
    answer('dismiss');
    set(confirmation, message);
    set(visible, true);
    stop();
    settle = onAnswer;
  }

  return {
    alternative,
    confirm,
    confirmation,
    dismiss,
    open,
    visible,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useConfirmStore, import.meta.hot));
