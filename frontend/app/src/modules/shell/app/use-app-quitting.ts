import type { Ref } from 'vue';

interface UseAppQuittingInternalReturn {
  quitting: Readonly<Ref<boolean>>;
  startQuitting: () => void;
}

/**
 * Tracks whether the app is shutting down.
 *
 * Setting this swaps the whole UI for the shutdown screen, which unmounts the
 * notification popup along with the rest of the tree. That is what keeps the
 * teardown quiet: the backend goes away while requests are still in flight, and
 * their failures would otherwise surface as error notifications over a window
 * that is about to disappear.
 *
 * It is a plain flag rather than a route so the swap is synchronous and cannot
 * be delayed or vetoed by a navigation guard — any gap between the quit signal
 * and the UI going away is a gap where those errors show up.
 */
function useAppQuittingInternal(): UseAppQuittingInternalReturn {
  const quitting = shallowRef<boolean>(false);

  function startQuitting(): void {
    set(quitting, true);
  }

  return {
    quitting: readonly(quitting),
    startQuitting,
  };
}

export const useAppQuitting = createGlobalState(useAppQuittingInternal);
