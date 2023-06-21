export const useCopy = (source: Ref<string>) => {
  const copied = ref<boolean>(false);

  const { copy: copyText } = useClipboard({
    source
  });

  const { start, stop, isPending } = useTimeoutFn(
    () => {
      set(copied, false);
    },
    4000,
    { immediate: false }
  );

  const { start: startAnimation } = useTimeoutFn(
    () => {
      set(copied, true);
      start();
    },
    100,
    { immediate: false }
  );

  const copy = async (): Promise<void> => {
    await copyText();
    if (get(isPending)) {
      stop();
      set(copied, false);
    }
    startAnimation();
  };

  return { copy, copied };
};
