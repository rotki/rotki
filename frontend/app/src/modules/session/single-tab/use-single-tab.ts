import type { Ref } from 'vue';
import { useInterop } from '@/modules/shell/app/use-electron-interop';

const CHANNEL_NAME = 'rotki.session.single-tab';
// Upper bound for the random delay before a paused tab takes over a vacated session. Staggers
// concurrent paused tabs so the first to fire claims and cancels the rest (see scheduleReclaim).
const RECLAIM_MAX_JITTER_MS = 400;

interface TabMessage {
  type: 'claim' | 'release';
  tabId: string;
}

export interface UseSingleTabReturn {
  /** Whether this tab currently owns the session. `false` means another tab took over. */
  isActiveTab: Readonly<Ref<boolean>>;
  /** True when cross-tab coordination is available (web/docker + BroadcastChannel present). */
  supported: boolean;
  /** Announce this tab as the sole active session, superseding every other tab. */
  claim: () => void;
  /** Become active and reboot this tab clean (claim + full reload). */
  reclaim: () => void;
  /** Stop coordinating (logout): hand off to any paused tab, then drop the channel. */
  release: () => void;
}

// A collision-safe id that does not depend on crypto.randomUUID, which is undefined outside
// a secure context — a Docker instance reached over plain http on a LAN IP is not one.
function createTabId(): string {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}`;
}

/**
 * Same-browser single-active-tab coordination for the Docker/web deployment (issue #3156).
 *
 * The backend cannot tell two tabs of the same browser apart — they share one session
 * cookie — so ownership is negotiated purely on the frontend over a `BroadcastChannel`.
 * The newest tab to `claim()` becomes the active one; every other tab hears the claim and
 * flips `isActiveTab` to `false`, which the guard uses to stop its polling and websocket.
 * When the active tab goes away (close/reload/logout) it broadcasts a `release`, so a paused
 * tab takes over instead of being stranded behind the overlay.
 * Electron is inert here (a single window, session lifecycle already tied to the backend).
 */
function createSingleTab(): UseSingleTabReturn {
  const { isPackaged } = useInterop();
  const supported = !isPackaged && typeof BroadcastChannel !== 'undefined';
  const active = ref<boolean>(true);
  const tabId = supported ? createTabId() : '';

  let channel: BroadcastChannel | undefined;
  let reclaimTimer: ReturnType<typeof setTimeout> | undefined;
  // Set right before an intentional reload (reclaim) so our own `pagehide` does not broadcast
  // a release — that would tell the tab we just paused to take over and bounce ownership back.
  let reloading = false;

  function cancelScheduledReclaim(): void {
    if (reclaimTimer !== undefined) {
      clearTimeout(reclaimTimer);
      reclaimTimer = undefined;
    }
  }

  function scheduleReclaim(): void {
    if (reclaimTimer !== undefined)
      return;
    reclaimTimer = setTimeout(() => {
      reclaimTimer = undefined;
      reclaim();
    }, Math.floor(Math.random() * RECLAIM_MAX_JITTER_MS));
  }

  function ensureChannel(): BroadcastChannel | undefined {
    if (!supported)
      return undefined;
    if (!channel) {
      channel = new BroadcastChannel(CHANNEL_NAME);
      channel.onmessage = (event: MessageEvent<TabMessage>): void => {
        const data = event.data;
        // Our own messages are never echoed back, but guard on tabId defensively.
        if (!data || data.tabId === tabId)
          return;
        if (data.type === 'claim') {
          // Another tab became active: yield, and drop any takeover we had queued.
          cancelScheduledReclaim();
          set(active, false);
        }
        else if (data.type === 'release' && !get(active)) {
          scheduleReclaim();
        }
      };
    }
    return channel;
  }

  function claim(): void {
    if (!supported)
      return;
    cancelScheduledReclaim();
    set(active, true);
    ensureChannel()?.postMessage({ tabId, type: 'claim' } satisfies TabMessage);
  }

  function reclaim(): void {
    if (!supported)
      return;
    reloading = true;
    claim();
    window.location.reload();
  }

  function broadcastRelease(): void {
    // Only the active tab hands off; a paused tab closing must not wake the others.
    if (!supported || !get(active))
      return;
    ensureChannel()?.postMessage({ tabId, type: 'release' } satisfies TabMessage);
  }

  function release(): void {
    // Logout: hand off first (a paused tab reloads and lands on login too, since the shared
    // session is now gone), then drop the channel and reset for a future login on this tab.
    broadcastRelease();
    cancelScheduledReclaim();
    set(active, true);
    channel?.close();
    channel = undefined;
  }

  if (supported) {
    window.addEventListener('pagehide', () => {
      if (!reloading)
        broadcastRelease();
    });
  }

  return {
    claim,
    isActiveTab: readonly(active),
    reclaim,
    release,
    supported,
  };
}

// A global singleton (like the monitor/websocket services): the channel and tab id must
// outlive layout remounts — the login-to-app layout switch would otherwise tear the shared
// state down and drop the channel between subscribers.
export const useSingleTab = createGlobalState(createSingleTab);
