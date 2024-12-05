import type { Ref } from 'vue';

interface UseCopyReturn {
  copy: () => Promise<void>;
  copied: Ref<boolean>;
}

export function useCopy(source: Ref<string>): UseCopyReturn {
  const copied = ref<boolean>(false);

  const { copy: copyText } = useClipboard({
    source,
  });

  const { isPending, start, stop } = useTimeoutFn(() => {
    set(copied, false);
  }, 4000, { immediate: false });

  const { start: startAnimation } = useTimeoutFn(() => {
    set(copied, true);
    start();
  }, 100, { immediate: false });

  const copy = async (): Promise<void> => {
    await copyText();
    if (get(isPending)) {
      stop();
      set(copied, false);
    }
    startAnimation();
  };

  return { copied, copy };
}
