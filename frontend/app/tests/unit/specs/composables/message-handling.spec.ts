import { Blockchain } from '@rotki/common';
import { beforeAll, describe, expect, it, vi } from 'vitest';
import { SocketMessageType } from '@/types/websocket-messages';
import type { EvmChainInfo } from '@/types/api/chains';

vi.mock('@/store/notifications', () => ({
  useNotificationsStore: vi.fn().mockReturnValue({
    notify: vi.fn(),
  }),
}));

vi.mock('@/composables/balances/token-detection', () => ({
  useTokenDetection: vi.fn().mockReturnValue({
    detectTokens: vi.fn(),
  }),
}));

vi.mock('@/composables/info/chains', () => ({
  useSupportedChains: vi.fn().mockReturnValue({
    txEvmChains: computed(() => [
      {
        evmChainName: 'optimism',
        id: Blockchain.OPTIMISM,
        type: 'evm',
        image: '',
        name: 'Optimism',
        nativeToken: 'ETH',
      } satisfies EvmChainInfo,
    ]),
    txChains: computed(() => [
      {
        evmChainName: 'optimism',
        id: Blockchain.OPTIMISM,
        type: 'evm',
        name: 'Optimism',
        image: '',
        nativeToken: 'ETH',
      } satisfies EvmChainInfo,
    ]),
    getChain: () => Blockchain.OPTIMISM,
    getChainName: () => Blockchain.OPTIMISM,
    getNativeAsset: (chain: Blockchain) => chain,
    isEvm: (_chain: Blockchain) => true,
  }),
}));

describe('composables::message-handling', () => {
  beforeAll(() => {
    const pinia = createPinia();
    setActivePinia(pinia);
  });
  it('notifies the user and runs token detection', async () => {
    const { handleMessage } = useMessageHandling();
    const { notify } = useNotificationsStore();
    const { canRequestData } = storeToRefs(useSessionAuthStore());
    const { detectTokens } = useTokenDetection(Blockchain.OPTIMISM);
    set(canRequestData, true);
    await handleMessage(
      JSON.stringify({
        type: SocketMessageType.EVM_ACCOUNTS_DETECTION,
        data: [
          {
            chain: 'optimism',
            address: '0xdead',
          },
        ],
      }),
    );

    expect(detectTokens).toHaveBeenCalledTimes(1);
    expect(detectTokens).toHaveBeenCalledWith(['0xdead']);
    expect(notify).toHaveBeenCalledTimes(1);
  });
});
