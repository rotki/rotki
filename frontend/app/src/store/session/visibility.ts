import type { Nullable } from '@rotki/common';
import type { Pinned } from '@/types/session';

export const useAreaVisibilityStore = defineStore('session/visibility', () => {
  const showAbout = ref(false);
  const pinned = ref<Nullable<Pinned>>(null);
  const showDrawer = ref(false);
  const showNotificationBar = ref(false);
  const showHelpBar = ref(false);
  const showNotesSidebar = ref(false);
  const showPinned = ref(false);

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
    toggleDrawer,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useAreaVisibilityStore, import.meta.hot));
