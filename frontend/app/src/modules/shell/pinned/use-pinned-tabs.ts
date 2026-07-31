import type { Nullable } from '@rotki/common';
import type { ComputedRef, Ref } from 'vue';
import type { MessageKey } from '@/message-key';
import type { PinnedName } from '@/modules/session/types';
import { useAreaVisibilityStore } from '@/modules/core/common/use-area-visibility-store';
import { PINNED_PANELS } from '@/modules/shell/pinned/pinned-registry';

interface PinnedTab {
  name: PinnedName;
  icon: string;
  labelKey: MessageKey;
}

export interface UsePinnedTabsReturn {
  /** The pinned panels as tab descriptors (name + registry label + icon), in tab order. */
  tabs: ComputedRef<PinnedTab[]>;
  /** The panel currently shown in the rail. */
  activePinnedId: Ref<Nullable<PinnedName>>;
  /** Bring a pinned panel to the front and reveal the rail. */
  focus: (id: PinnedName) => void;
  /** Remove a pinned panel's tab. */
  close: (id: PinnedName) => void;
}

/**
 * Shared, registry-derived view of the pinned rail's tabs. Both the in-rail tab
 * strip and the top-bar indicator switcher read from here so their labels, icons
 * and focus/close behaviour stay identical.
 */
export function usePinnedTabs(): UsePinnedTabsReturn {
  const store = useAreaVisibilityStore();
  const { activePinnedId, pinnedPanels } = storeToRefs(store);

  const tabs = computed<PinnedTab[]>(() => get(pinnedPanels).map(panel => ({
    icon: PINNED_PANELS[panel.name].icon,
    labelKey: PINNED_PANELS[panel.name].labelKey,
    name: panel.name,
  })));

  return {
    activePinnedId,
    close: store.unpinPanel,
    focus: store.focusPanel,
    tabs,
  };
}
