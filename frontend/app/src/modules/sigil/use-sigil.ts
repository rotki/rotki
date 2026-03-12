import type { SigilEvent, SigilEventMap } from '@/modules/sigil/types';
import { startPromise } from '@shared/utils';
import { createSharedComposable } from '@vueuse/core';
import { sigilBus } from '@/modules/sigil/event-bus';
import { useBalancesSummaryHandler } from '@/modules/sigil/handlers/balances-summary';
import { useExchangesSummaryHandler } from '@/modules/sigil/handlers/exchanges-summary';
import { useHistorySyncHandler } from '@/modules/sigil/handlers/history-sync';
import { useSessionConfigHandler } from '@/modules/sigil/handlers/session-config';
import { enqueue, startQueue, stopQueue, WEBSITE_ID } from '@/modules/sigil/use-sigil-queue';
import { router } from '@/router';
import { useMainStore } from '@/store/main';
import { useSessionAuthStore } from '@/store/session/auth';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { logger } from '@/utils/logging';

/**
 * Route params that are safe to include in analytics URLs.
 * These are enum / category values, never user-specific data.
 * Any param NOT listed here is redacted to its placeholder name.
 */
const SAFE_PARAMS: ReadonlySet<string> = new Set([
  'location', // staking: eth2, liquity, lido-csm, kraken
  'exchange', // balances/exchange: binance, kraken, etc.
  'tab', // UI tab names: accounts, validators, etc.
]);

/**
 * Builds a safe analytics URL from a route record.
 *
 * Uses the matched route pattern as the base, then selectively
 * resolves params that are on the safe-list. Sensitive params
 * stay as their placeholder (e.g., `:identifier`).
 */
function buildSafeUrl(to: { name?: string | symbol | null | undefined; params: Record<string, string | string[]>; matched: { path: string }[] }): string {
  const pattern = to.matched.at(-1)?.path ?? String(to.name ?? '/');

  return pattern.replace(/:(\w+)([*?]?)/g, (placeholder, param: string) => {
    const value = to.params[param];
    if (!value || !SAFE_PARAMS.has(param))
      return placeholder;

    const resolved = Array.isArray(value) ? value.join('/') : value;
    return resolved || placeholder;
  });
}

export const useSigil = createSharedComposable(() => {
  const { logged } = storeToRefs(useSessionAuthStore());
  const { submitUsageAnalytics } = storeToRefs(useGeneralSettingsStore());
  const { isDevelop } = storeToRefs(useMainStore());

  // Initialize handlers in Vue context so they can resolve stores/composables.
  const collectSessionConfig = useSessionConfigHandler();
  const collectExchangesSummary = useExchangesSummaryHandler();
  const collectBalancesSummary = useBalancesSummaryHandler();
  const collectHistorySync = useHistorySyncHandler();

  const isSigilActive = ref<boolean>(false);
  const emittedEvents = new Set<SigilEvent>();
  let removeRouterHook: (() => void) | undefined;

  function chronicle<T extends SigilEvent>(event: T, data: SigilEventMap[T]): void {
    if (!get(isSigilActive))
      return;

    if (emittedEvents.has(event))
      return;

    emittedEvents.add(event);
    const payload: Record<string, unknown> = { ...data };
    const route = router.currentRoute.value;
    startPromise(enqueue({
      url: buildSafeUrl(route),
      name: event,
      data: payload,
      timestamp: Date.now(),
    }));
    logger.debug(`[sigil] chronicle: ${event}`);
  }

  function onSessionReady(): void {
    chronicle('session_config', collectSessionConfig());
    chronicle('exchanges_summary', collectExchangesSummary());
  }

  function onBalancesLoaded(): void {
    chronicle('balances_summary', collectBalancesSummary());
  }

  function onHistoryReady(): void {
    startPromise(collectHistorySync().then((payload) => {
      if (payload)
        chronicle('history_sync', payload);
    }));
  }

  function registerPageTracking(): void {
    if (removeRouterHook)
      return;

    removeRouterHook = router.afterEach((to) => {
      const url = buildSafeUrl(to);
      startPromise(enqueue({ url, timestamp: Date.now() }));
    });
  }

  function unregisterPageTracking(): void {
    if (removeRouterHook) {
      removeRouterHook();
      removeRouterHook = undefined;
    }
  }

  function activate(): void {
    startQueue();
    registerPageTracking();
    sigilBus.on('session:ready', onSessionReady);
    sigilBus.on('balances:loaded', onBalancesLoaded);
    sigilBus.on('history:ready', onHistoryReady);
  }

  function deactivate(): void {
    sigilBus.off('session:ready', onSessionReady);
    sigilBus.off('balances:loaded', onBalancesLoaded);
    sigilBus.off('history:ready', onHistoryReady);
    unregisterPageTracking();
    stopQueue();
    emittedEvents.clear();
  }

  // Only activate on production builds with analytics opted in.
  // VITE_SIGIL_DEBUG=true overrides the production-only gate for local testing.
  const sigilDebug = !!import.meta.env.VITE_SIGIL_DEBUG;

  watchImmediate(
    computed<boolean>(() => !!WEBSITE_ID && get(logged) && get(submitUsageAnalytics) && (sigilDebug || !get(isDevelop))),
    (active) => {
      set(isSigilActive, active);
      if (active) {
        activate();
      }
      else {
        deactivate();
      }
    },
  );

  onScopeDispose(deactivate);

  return { chronicle };
});
