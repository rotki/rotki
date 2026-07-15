import type { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { Blockchain } from '@rotki/common';
import { type Mock, vi } from 'vitest';

type SupportedChainsReturn = ReturnType<typeof useSupportedChains>;

/**
 * Builds the `useSupportedChains` mock used by ~58 specs. Provides sensible
 * defaults for the commonly-touched members (`getChainName` echoes its input,
 * the predicates return `false`, the list getters resolve to empty arrays) so a
 * spec only has to override what it actually asserts on, and won't break when an
 * unrelated code path reaches for a member it never mocked.
 *
 * ```ts
 * const { getChainName } = vi.hoisted(() => ({ getChainName: vi.fn((c: string) => c) }));
 * vi.mock('@/modules/core/common/use-supported-chains', () =>
 *   mockUseSupportedChains({ getChainName }),
 * );
 * ```
 */
export function mockUseSupportedChains(
  overrides: Partial<SupportedChainsReturn> = {},
): { useSupportedChains: Mock } {
  const defaults: Partial<SupportedChainsReturn> = {
    allTxChainsInfo: computed(() => []),
    bitcoinChainsData: computed(() => []),
    decodableTxChainsInfo: computed(() => []),
    evmAndEvmLikeTxChainsInfo: computed(() => []),
    evmChains: computed(() => []),
    evmChainsData: computed(() => []),
    evmLikeChainsData: computed(() => []),
    getChain: (_location: string, defaultValue?: Blockchain): Blockchain => defaultValue ?? Blockchain.ETH,
    getChainName: (location: string): string => location,
    getEvmChainName: (): string | undefined => undefined,
    getNativeAsset: (chain: string): string => chain,
    isBtcChains: (): boolean => false,
    isDecodableChains: (): boolean => false,
    isEvm: (): boolean => false,
    isEvmCompatible: (): boolean => false,
    isEvmLikeChains: (): boolean => false,
    isSolanaChains: (): boolean => false,
    matchChain: (): Blockchain | undefined => undefined,
    refreshSupportedChains: async (): Promise<void> => {},
    solanaChainsData: computed(() => []),
    supportedChains: ref([]),
    supportsTransactions: (): boolean => false,
    txChainsToLocation: computed(() => []),
    txEvmChains: computed(() => []),
  };

  return {
    useSupportedChains: vi.fn(() => ({ ...defaults, ...overrides })),
  };
}
