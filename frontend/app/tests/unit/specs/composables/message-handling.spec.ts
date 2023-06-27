import { Blockchain } from '@rotki/common/lib/blockchain';
import { SocketMessageType } from '@/types/websocket-messages';
import { type EvmChainInfo } from '@/types/api/chains';

vi.mock('@/store/notifications', async () => ({
  useNotificationsStore: vi.fn().mockReturnValue({
    notify: vi.fn()
  })
}));

vi.mock('@/composables/balances/token-detection', () => ({
  useTokenDetection: vi.fn().mockReturnValue({
    detectTokens: vi.fn()
  })
}));

vi.mock('@/composables/info/chains', () => ({
  useSupportedChains: vi.fn().mockReturnValue({
    txEvmChains: computed(() => [
      {
        evmChainName: 'optimism',
        id: Blockchain.OPTIMISM,
        type: 'evm',
        name: 'Optimism',
        nativeAsset: 'ETH'
      } satisfies EvmChainInfo
    ]),
    getChain: () => Blockchain.OPTIMISM,
    getChainName: () => Blockchain.OPTIMISM,
    getNativeAsset: (chain: Blockchain) => chain
  })
}));

describe('composables::message-handling', () => {
  beforeAll(() => {
    const pinia = createPinia();
    setActivePinia(pinia);
  });
  test('notifies the user and runs token detection', async () => {
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
            evm_chain: 'optimism',
            address: '0xdead'
          }
        ]
      })
    );

    expect(detectTokens).toHaveBeenCalledTimes(1);
    expect(detectTokens).toHaveBeenCalledWith(['0xdead']);
    expect(notify).toHaveBeenCalledTimes(1);
  });
});
