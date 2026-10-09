import type { MaybeRefOrGetter, Ref } from 'vue';

interface UseCopyReturn {
  copy: () => Promise<void>;
  copied: Readonly<Ref<boolean>>;
}

/**
 * One clipboard for the whole app, the copied text passed at copy time. `useClipboard` queries the
 * clipboard permissions and listens for their changes in every component that calls it, which a
 * table repeated per row of copy buttons.
 */
export const useSharedClipboard = createSharedComposable(() => useClipboard());

export function useCopy(source: MaybeRefOrGetter<string>): UseCopyReturn {
  const copied = shallowRef<boolean>(false);

  const { copy: copyClipboard } = useSharedClipboard();
  const copyText = async (): Promise<void> => copyClipboard(toValue(source));

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

  return { copied: readonly(copied), copy };
}
