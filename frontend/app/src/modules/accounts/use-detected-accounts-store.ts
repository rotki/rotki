import type { EvmChainLikeAddress } from '@/modules/history/events/event-payloads';

/** Addresses compare case-insensitively, since EVM checksumming only changes the case. */
export function accountKey({ address, chain }: EvmChainLikeAddress): string {
  return `${chain}:${address.toLowerCase()}`;
}

/** A manual account addition, as detection has to know it to leave its accounts alone. */
interface UserAddition {
  readonly id: number;
  /** Lower-cased, like {@link accountKey}. */
  readonly addresses: readonly string[];
  /** The chain added to, or `undefined` for an addition that spans every EVM chain. */
  readonly chain?: string;
  readonly finished: boolean;
}

/**
 * The accounts that EVM account detection started tracking since login, so the accounts table can
 * mark them in place of a notification.
 *
 * @remarks
 * Plain state on purpose: the store reset at logout clears it, so a detection is news until the
 * user logs out, and the next user on the same window starts without marks.
 */
export const useDetectedAccountsStore = defineStore('accounts/detected', () => {
  const detected = ref<EvmChainLikeAddress[]>([]);

  /** What the last Detect run found, for the outcome its button reports. Unset while it runs. */
  const lastRun = shallowRef<EvmChainLikeAddress[]>();

  /**
   * The manual additions a detection run must not claim: every one still in flight, and every one
   * that finished since the run began.
   *
   * @remarks
   * A run finds accounts by comparing the store before and after it, so it would claim a manual
   * addition too. Each is recorded when submitted, not when it finishes: the backend saves the
   * accounts before the app polls the addition's result, so a detection re-read can see them first.
   */
  const userAdditions = ref<UserAddition[]>([]);
  let nextAdditionId = 0;

  const detectedKeys = computed<Set<string>>(() => new Set(get(detected).map(accountKey)));

  function record(accounts: EvmChainLikeAddress[]): void {
    const keys = new Set(get(detectedKeys));
    const added = accounts.filter((account) => {
      const key = accountKey(account);
      if (keys.has(key))
        return false;

      keys.add(key);
      return true;
    });

    if (added.length > 0)
      set(detected, [...get(detected), ...added]);
  }

  function setLastRun(accounts: EvmChainLikeAddress[] | undefined): void {
    set(lastRun, accounts);
  }

  /** Drops the marks of one address, for the user who has seen them and wants the row back to normal. */
  function dismiss(address: string): void {
    const normalized = address.toLowerCase();
    set(detected, get(detected).filter(account => account.address.toLowerCase() !== normalized));
  }

  /** Forgets the additions that finished before this run, keeping the ones still in flight. */
  function beginRun(): void {
    set(userAdditions, get(userAdditions).filter(addition => !addition.finished));
  }

  /** @returns the id to hand {@link finishUserAddition} once the addition settles, however it ends. */
  function startUserAddition(chain: string | undefined, addresses: string[]): number {
    const id = nextAdditionId++;
    set(userAdditions, [...get(userAdditions), { addresses: addresses.map(address => address.toLowerCase()), chain, finished: false, id }]);
    return id;
  }

  function finishUserAddition(id: number): void {
    set(userAdditions, get(userAdditions).map(addition => addition.id === id ? { ...addition, finished: true } : addition));
  }

  function wasAddedByUser({ address, chain }: EvmChainLikeAddress): boolean {
    const normalized = address.toLowerCase();
    return get(userAdditions).some(addition =>
      (addition.chain === undefined || addition.chain === chain) && addition.addresses.includes(normalized));
  }

  function isDetected(chain: string, address: string): boolean {
    return get(detectedKeys).has(accountKey({ address, chain }));
  }

  function detectedChains(address: string): string[] {
    const normalized = address.toLowerCase();
    return get(detected)
      .filter(account => account.address.toLowerCase() === normalized)
      .map(account => account.chain);
  }

  return {
    beginRun,
    detected,
    detectedChains,
    dismiss,
    finishUserAddition,
    isDetected,
    lastRun,
    record,
    setLastRun,
    startUserAddition,
    userAdditions,
    wasAddedByUser,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useDetectedAccountsStore, import.meta.hot));
