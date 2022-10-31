import { Nullable } from '@rotki/common';
import { Pinned } from '@/store/session/types';

export const useAreaVisibilityStore = defineStore('session/visibility', () => {
  const showAbout = ref(false);
  const pinned = ref<Nullable<Pinned>>(null);
  const showDrawer = ref(false);
  const isMini = ref(false);
  const showNotificationBar = ref(false);
  const showHelpBar = ref(false);
  const showNotesSidebar = ref(false);
  const showPinned = ref(false);

  const toggleDrawer = () => {
    if (!get(showDrawer)) {
      set(showDrawer, !get(showDrawer));
      set(isMini, false);
    } else {
      set(isMini, !get(isMini));
    }
  };

  const reset = () => {
    set(showAbout, false);
    set(pinned, null);
    set(showDrawer, false);
    set(isMini, false);
    set(showNotificationBar, false);
    set(showHelpBar, false);
    set(showNotesSidebar, false);
    set(showPinned, false);
  };

  watch(pinned, (current, prev) => {
    if (current !== prev) {
      set(showPinned, !!current);
    }
  });

  return {
    showAbout,
    showHelpBar,
    showNotificationBar,
    showNotesSidebar,
    isMini,
    showDrawer,
    pinned,
    showPinned,
    toggleDrawer,
    reset
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(
    acceptHMRUpdate(useAreaVisibilityStore, import.meta.hot)
  );
}
