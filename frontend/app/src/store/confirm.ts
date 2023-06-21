import { type DialogType } from '@/types/dialogs';

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

const defaultMessage = (): ConfirmationMessage => ({
  title: '',
  message: '',
  type: 'warning',
  singleAction: false
});

export const useConfirmStore = defineStore('confirm', () => {
  const visible = ref(false);
  const confirmation: Ref<ConfirmationMessage> = ref(defaultMessage());
  const onConfirm: Ref<Func> = ref(defaultFunc);
  const onDismiss: Ref<Func> = ref(defaultFunc);

  const { start, stop } = useTimeoutFn(
    () => {
      set(confirmation, defaultMessage());
    },
    3000,
    { immediate: false }
  );

  const show = (
    message: ConfirmationMessage,
    onConfirmFunc: Func,
    onDismissFunc?: Func
  ) => {
    set(confirmation, message);
    set(onConfirm, onConfirmFunc);
    if (onDismissFunc) {
      set(onDismiss, onDismissFunc);
    }
    set(visible, true);
    stop();
  };

  const reset = () => {
    set(visible, false);
    set(onConfirm, defaultFunc);
    set(onDismiss, defaultFunc);
    start();
  };

  const dismiss = async () => {
    const method = get(onDismiss);
    reset();
    await method();
  };

  const confirm = async () => {
    const method = get(onConfirm);
    reset();
    await method();
  };

  return {
    visible,
    confirmation,
    confirm,
    show,
    dismiss
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useConfirmStore, import.meta.hot));
}
