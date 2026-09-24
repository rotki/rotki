import type { DialogType } from '@/modules/core/common/dialogs';

interface ConfirmationMessage {
  title: string;
  message: string;
  type?: DialogType;
  singleAction?: boolean;
  primaryAction?: string;
  /** Label of the button that backs out, which Escape does too; defaults to "Cancel". */
  secondaryAction?: string;
  /** Label of a third button for a different outcome than confirming, shown only when set. */
  alternativeAction?: string;
}

type AwaitableFunc = () => Promise<void>;

type VoidFunc = () => void;

type Func = VoidFunc | AwaitableFunc;

const defaultFunc: Func = () => {};

function defaultMessage(): ConfirmationMessage {
  return {
    message: '',
    singleAction: false,
    title: '',
    type: 'warning',
  };
}

export const useConfirmStore = defineStore('confirm', () => {
  const visible = ref(false);
  const confirmation = ref<ConfirmationMessage>(defaultMessage());
  const onConfirm = ref<Func>(defaultFunc);
  const onDismiss = ref<Func>(defaultFunc);
  const onAlternative = ref<Func>(defaultFunc);

  const { start, stop } = useTimeoutFn(
    () => {
      set(confirmation, defaultMessage());
    },
    3000,
    { immediate: false },
  );

  /**
   * Opens the confirmation.
   *
   * @remarks
   * `onDismissFunc` runs whenever the user backs out, by the button or by Escape, so it must never
   * do anything the user did not ask for. A different outcome goes in `onAlternativeFunc`, with its
   * label in `alternativeAction`.
   */
  const show = (message: ConfirmationMessage, onConfirmFunc: Func, onDismissFunc?: Func, onAlternativeFunc?: Func): void => {
    set(confirmation, message);
    set(onConfirm, onConfirmFunc);
    if (onDismissFunc)
      set(onDismiss, onDismissFunc);
    if (onAlternativeFunc)
      set(onAlternative, onAlternativeFunc);

    set(visible, true);
    stop();
  };

  const reset = (): void => {
    set(visible, false);
    set(onConfirm, defaultFunc);
    set(onDismiss, defaultFunc);
    set(onAlternative, defaultFunc);
    start();
  };

  const alternative = async (): Promise<void> => {
    const method = get(onAlternative);
    reset();
    await method();
  };

  const dismiss = async (): Promise<void> => {
    const method = get(onDismiss);
    reset();
    await method();
  };

  const confirm = async (): Promise<void> => {
    const method = get(onConfirm);
    reset();
    await method();
  };

  return {
    alternative,
    confirm,
    confirmation,
    dismiss,
    show,
    visible,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useConfirmStore, import.meta.hot));
