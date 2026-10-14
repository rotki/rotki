import type { InjectionKey, Ref } from 'vue';

/**
 * Set by a page that shows the history events as one section among others, such as ETH staking.
 *
 * In a section the events take the page's frame instead of a card of their own, and the page's
 * refresh covers them: the view drops its own refresh button and reloads whenever `reloads` ticks.
 */
interface HistoryEventsSectionContext {
  readonly reloads: Readonly<Ref<number>>;
}

interface ProvideHistoryEventsSectionReturn {
  /** Asks the events section to read its events again. */
  reload: () => void;
}

const HistoryEventsSectionKey: InjectionKey<HistoryEventsSectionContext> = Symbol('history-events-section');

export function provideHistoryEventsSection(): ProvideHistoryEventsSectionReturn {
  const reloads = ref<number>(0);
  provide(HistoryEventsSectionKey, { reloads: readonly(reloads) });
  return {
    reload: (): void => {
      set(reloads, get(reloads) + 1);
    },
  };
}

export function useHistoryEventsSection(): HistoryEventsSectionContext | undefined {
  return inject(HistoryEventsSectionKey, undefined);
}
