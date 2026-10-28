import type { ComputedRef } from 'vue';
import type { Router } from 'vue-router';
import { omit } from 'es-toolkit';
import { type AccountDetailsView, isAccountDetailsView } from '@/modules/accounts/details/account-details-views';
import { firstQueryValue } from '@/modules/core/table/route';

const ACCOUNT_KEY = 'account';
const VIEW_KEY = 'view';

/** The query keys the details drawer owns; the accounts table carries them over on its own writes. */
export const ACCOUNT_DETAILS_QUERY_KEYS = [ACCOUNT_KEY, VIEW_KEY] as const;

/** How an open lands in history: a new entry, or the current one rewritten. */
export type AccountDetailsOpenMode = 'push' | 'replace';

interface UseAccountDetailsRouteReturn {
  /** Group id of the account whose details are open, `undefined` while the drawer is closed. */
  accountId: ComputedRef<string | undefined>;
  /** The tab the URL asks for, `undefined` when it names none or one that does not exist. */
  view: ComputedRef<AccountDetailsView | undefined>;
  open: (accountId: string, mode: AccountDetailsOpenMode) => Promise<void>;
  close: () => Promise<void>;
  /** Drops the drawer's keys from the current entry, for a key that names no account. */
  discard: () => Promise<void>;
  setView: (view: AccountDetailsView) => Promise<void>;
}

/** The vue-router position of the current history entry, `undefined` when it carries none. */
function historyPosition(router: Router): number | undefined {
  const position = router.options.history.state.position;
  return typeof position === 'number' ? position : undefined;
}

/**
 * Keeps the accounts details drawer in the URL, so Back closes it and a link or a reload reopens it.
 *
 * @remarks
 * The caller picks how an open lands: a push when nothing shows yet, so Back closes it, a replace
 * when it only switches the account. Switching tabs replaces too, so Back never steps through tabs.
 *
 * Closing goes back only while the current entry is still the one the open pushed; that leaves no
 * entry behind that would reopen the drawer. Anything else (a drawer that arrived open from a link
 * or a reload, or a table write that pushed a further entry on top) has no clean entry to go back
 * to, so closing drops the keys from the current one instead.
 */
export function useAccountDetailsRoute(): UseAccountDetailsRouteReturn {
  const route = useRoute();
  const router = useRouter();

  /** History position of the entry this page pushed, while it is the drawer's own entry. */
  const pushedAt = shallowRef<number>();

  const accountId = computed<string | undefined>(() => firstQueryValue(get(route).query[ACCOUNT_KEY]) || undefined);

  const view = computed<AccountDetailsView | undefined>(() => {
    const value = firstQueryValue(get(route).query[VIEW_KEY]);
    return isAccountDetailsView(value) ? value : undefined;
  });

  async function open(id: string, mode: AccountDetailsOpenMode): Promise<void> {
    const query = { ...omit(get(route).query, [VIEW_KEY]), [ACCOUNT_KEY]: id };
    if (mode === 'replace') {
      await router.replace({ query });
      return;
    }

    await router.push({ query });
    set(pushedAt, historyPosition(router));
  }

  async function discard(): Promise<void> {
    set(pushedAt, undefined);
    await router.replace({ query: omit(get(route).query, [...ACCOUNT_DETAILS_QUERY_KEYS]) });
  }

  async function close(): Promise<void> {
    if (!get(accountId))
      return;

    const ownEntry = get(pushedAt);
    if (ownEntry !== undefined && ownEntry === historyPosition(router)) {
      set(pushedAt, undefined);
      router.back();
      return;
    }

    await discard();
  }

  async function setView(next: AccountDetailsView): Promise<void> {
    await router.replace({ query: { ...get(route).query, [VIEW_KEY]: next } });
  }

  watch(accountId, (id) => {
    if (!id)
      set(pushedAt, undefined);
  });

  return {
    accountId,
    close,
    discard,
    open,
    setView,
    view,
  };
}
