import type { Ref } from 'vue';

interface UseAutoLogoutNoticeReturn {
  /** The idle period, in minutes, that ended the last session, while the login screen should say so. */
  idleMinutes: Readonly<Ref<number | undefined>>;
  show: (minutes: number) => void;
  dismiss: () => void;
}

/**
 * Why the user is back at the login screen after an idle logout.
 *
 * @remarks
 * Global rather than shared, so it outlives the logged-in layout that sets it and is still there
 * for the login layout that reads it.
 */
export const useAutoLogoutNotice = createGlobalState((): UseAutoLogoutNoticeReturn => {
  const idleMinutes = shallowRef<number>();

  const show = (minutes: number): void => {
    set(idleMinutes, minutes);
  };

  const dismiss = (): void => {
    set(idleMinutes, undefined);
  };

  return {
    dismiss,
    idleMinutes: readonly(idleMinutes),
    show,
  };
});
