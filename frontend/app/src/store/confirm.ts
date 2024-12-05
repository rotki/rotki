import type { DialogType } from '@/types/dialogs';

interface ConfirmationMessage {
  title: string;
  message: string;
  type?: DialogType;
  singleAction?: boolean;
  primaryAction?: string;
  secondaryAction?: string;
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

  const { start, stop } = useTimeoutFn(
    () => {
      set(confirmation, defaultMessage());
    },
    3000,
    { immediate: false },
  );

  const show = (message: ConfirmationMessage, onConfirmFunc: Func, onDismissFunc?: Func): void => {
    set(confirmation, message);
    set(onConfirm, onConfirmFunc);
    if (onDismissFunc)
      set(onDismiss, onDismissFunc);

    set(visible, true);
    stop();
  };

  const reset = (): void => {
    set(visible, false);
    set(onConfirm, defaultFunc);
    set(onDismiss, defaultFunc);
    start();
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
    confirm,
    confirmation,
    dismiss,
    show,
    visible,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useConfirmStore, import.meta.hot));
