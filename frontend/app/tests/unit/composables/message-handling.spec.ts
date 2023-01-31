import { Blockchain } from '@rotki/common/lib/blockchain';
import { useMessageHandling } from '@/composables/message-handling';
import { SocketMessageType } from '@/types/websocket-messages';
import { useNotificationsStore } from '@/store/notifications';
import { useTokenDetection } from '@/composables/balances/token-detection';
import { type EvmChainInfo } from '@/types/api/chains';
import { useSessionAuthStore } from '@/store/session/auth';

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
    getChain: () => Blockchain.OPTIMISM
  })
}));

describe('useMessageHandling', () => {
  beforeAll(() => {
    const pinia = createPinia();
    setActivePinia(pinia);
  });
  test('notifies the user and runs token detection', async () => {
    const { handleMessage } = useMessageHandling();
    const { notify } = useNotificationsStore();
    const { logged } = storeToRefs(useSessionAuthStore());
    const { detectTokens } = useTokenDetection(Blockchain.OPTIMISM);
    set(logged, true);
    await handleMessage(
      JSON.stringify({
        type: SocketMessageType.EVM_ADDRESS_MIGRATION,
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
