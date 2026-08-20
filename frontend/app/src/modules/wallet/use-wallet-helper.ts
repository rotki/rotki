import type { Blockchain } from '@rotki/common';
import type { RecentTransaction } from '@/modules/wallet/types';
import { useBlockchainBalances } from '@/modules/balances/use-blockchain-balances';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useHistoryTransactions } from '@/modules/history/events/tx/use-history-transactions';
import { EIP155 } from './constants';

interface UseWalletHelperReturn {
  getEvmChainNameFromChainId: (chainId: number | bigint) => string | undefined;
  getChainFromChainId: (chainId: number | bigint) => Blockchain | undefined;
  getChainIdFromChain: (chain: string) => number | undefined;
  getChainIdFromNamespace: (namespace: string) => number;
  updateStatePostTransaction: (tx?: RecentTransaction) => Promise<void>;
  getEip155ChainId: (chainId: string | number) => string;
}

export function useWalletHelper(): UseWalletHelperReturn {
  const { allEvmChains, getChain, getEvmChainName } = useSupportedChains();
  const { refreshBlockchainBalances } = useBlockchainBalances();
  const { addTransactionHash } = useHistoryTransactions();

  /**
   * The chain id is whatever the connected wallet reports, which is not
   * constrained to the chains rotki supports. An unknown id resolves to nothing:
   * defaulting it to ethereum made a wallet sitting on an unsupported chain look
   * like it was on mainnet, so the "wrong network" warning never appeared.
   */
  function getEvmChainNameFromChainId(chainId: number | bigint): string | undefined {
    const id = typeof chainId === 'bigint' ? Number(chainId) : chainId;
    return get(allEvmChains).find(item => item.id === id)?.name;
  }

  function getChainFromChainId(chainId: number | bigint): Blockchain | undefined {
    const name = getEvmChainNameFromChainId(chainId);
    return name === undefined ? undefined : getChain(name);
  }

  /**
   * `chain` is a rotki blockchain id (`eth`), while `allEvmChains` is keyed by the
   * evm chain name (`ethereum`), so the two have to be bridged. They happen to be
   * identical for every chain but ethereum, which is why matching the id directly
   * used to work: it missed and fell through to a hardcoded `1`.
   */
  const getChainIdFromChain = (chain: string): number | undefined => {
    const name = getEvmChainName(chain) ?? chain;
    return get(allEvmChains).find(item => item.name === name)?.id;
  };

  const getEip155ChainId = (chainId: string | number): string => `${EIP155}:${chainId}`;

  const getChainIdFromNamespace = (namespace: string): number => Number(namespace.replace(`${EIP155}:`, ''));

  const updateStatePostTransaction = async (tx?: RecentTransaction): Promise<void> => {
    if (!tx)
      return;

    const { chain, hash, initiatorAddress: address } = tx;

    await Promise.all([
      refreshBlockchainBalances({
        blockchain: chain,
      }),
      addTransactionHash({
        associatedAddress: address,
        blockchain: chain,
        txRef: hash,
      }),
    ]);
  };

  return {
    getChainFromChainId,
    getChainIdFromChain,
    getChainIdFromNamespace,
    getEip155ChainId,
    getEvmChainNameFromChainId,
    updateStatePostTransaction,
  };
}
