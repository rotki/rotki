import { Blockchain } from '@rotki/common/lib/blockchain';

export function useAccountsAddresses() {
  const { btcAddresses, bchAddresses } = storeToRefs(useBtcAccountsStore());
  const { ethAddresses } = storeToRefs(useEthAccountsStore());
  const {
    ksmAddresses,
    dotAddresses,
    avaxAddresses,
    optimismAddresses,
    polygonAddresses,
    arbitrumAddresses,
    baseAddresses,
    gnosisAddresses,
    scrollAddresses,
  } = storeToRefs(useChainsAccountsStore());

  const allAddressMapping = computed<Record<string, string[]>>(() => ({
    [Blockchain.BTC]: get(btcAddresses),
    [Blockchain.BCH]: get(bchAddresses),
    [Blockchain.ETH]: get(ethAddresses),
    [Blockchain.KSM]: get(ksmAddresses),
    [Blockchain.DOT]: get(dotAddresses),
    [Blockchain.AVAX]: get(avaxAddresses),
    [Blockchain.OPTIMISM]: get(optimismAddresses),
    [Blockchain.POLYGON_POS]: get(polygonAddresses),
    [Blockchain.ARBITRUM_ONE]: get(arbitrumAddresses),
    [Blockchain.BASE]: get(baseAddresses),
    [Blockchain.GNOSIS]: get(gnosisAddresses),
    [Blockchain.SCROLL]: get(scrollAddresses),
  }));

  return { allAddressMapping };
}
