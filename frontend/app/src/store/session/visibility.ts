import type { Nullable } from '@rotki/common';
import type { Pinned } from '@/types/session';

export const useAreaVisibilityStore = defineStore('session/visibility', () => {
  const showAbout = ref<boolean>(false);
  const pinned = ref<Nullable<Pinned>>(null);
  const showDrawer = ref<boolean>(false);
  const showNotificationBar = ref<boolean>(false);
  const showHelpBar = ref<boolean>(false);
  const showNotesSidebar = ref<boolean>(false);
  const showPinned = ref<boolean>(false);
  const showPrivacyModeMenu = ref<boolean>(false);

  const toggleDrawer = (): void => {
    set(showDrawer, !get(showDrawer));
  };

  watch(pinned, (current, prev) => {
    if (current !== prev)
      set(showPinned, !!current);
  });

  const { isXlAndDown } = useBreakpoint();
  const isMini = logicAnd(logicNot(isXlAndDown), logicNot(showDrawer));

  const expanded = logicAnd(logicNot(isXlAndDown), showDrawer);

  return {
    expanded,
    isMini,
    pinned,
    showAbout,
    showDrawer,
    showHelpBar,
    showNotesSidebar,
    showNotificationBar,
    showPinned,
    showPrivacyModeMenu,
    toggleDrawer,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useAreaVisibilityStore, import.meta.hot));
