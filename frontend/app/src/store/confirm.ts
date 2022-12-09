import { type Ref } from 'vue';

interface ConfirmationMessage {
  title: string;
  message: string;
  primaryAction?: string;
  secondaryAction?: string;
}

type AwaitableFunc = () => Promise<void>;
type VoidFunc = () => void;
type Func = VoidFunc | AwaitableFunc;

const defaultOnConfirm: Func = () => {};

const defaultMessage = (): ConfirmationMessage => ({
  title: '',
  message: ''
});

export const useConfirmStore = defineStore('confirm', () => {
  const visible = ref(false);
  const confirmation: Ref<ConfirmationMessage> = ref(defaultMessage());
  const onConfirm: Ref<Func> = ref(defaultOnConfirm);

  const { start, stop } = useTimeoutFn(
    () => {
      set(confirmation, defaultMessage());
    },
    3000,
    { immediate: false }
  );

  const show = (message: ConfirmationMessage, method: Func) => {
    set(confirmation, message);
    set(onConfirm, method);
    set(visible, true);
    stop();
  };

  const dismiss = () => {
    set(visible, false);
    start();
  };

  const confirm = async () => {
    set(visible, false);
    const method = get(onConfirm);
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
