import type { EvmChainInfo } from '@/modules/api/types/chains';
import { assert, type Blockchain } from '@rotki/common';
import { mount } from '@vue/test-utils';
import { beforeAll, describe, expect, it, vi } from 'vitest';
import { useMessageHandling } from '@/modules/messaging';
import { SocketMessageType } from '@/modules/messaging/types';
import { useNotificationDispatcher } from '@/modules/notifications/use-notification-dispatcher';
import { useSessionAuthStore } from '@/store/session/auth';

vi.mock('@/store/notifications', async () => {
  const { shallowRef } = await import('vue');
  return {
    useNotificationsStore: vi.fn().mockReturnValue({
      data: shallowRef([]),
    }),
  };
});

vi.mock('@/modules/notifications/use-notification-dispatcher', () => ({
  useNotificationDispatcher: vi.fn().mockReturnValue({
    notify: vi.fn(),
  }),
}));

const { mockDetectTokens } = vi.hoisted((): { mockDetectTokens: ReturnType<typeof vi.fn> } => ({
  mockDetectTokens: vi.fn(),
}));
vi.mock('@/modules/balances/blockchain/use-token-detection-orchestrator', async () => {
  const { computed } = await import('vue');
  return {
    useTokenDetectionOrchestrator: vi.fn().mockReturnValue({
      detectTokens: mockDetectTokens,
      detectAllTokens: vi.fn(),
      useIsDetecting: vi.fn().mockReturnValue(computed(() => false)),
    }),
  };
});

vi.mock('@/modules/accounts/use-blockchain-account-management', () => ({
  useBlockchainAccountManagement: vi.fn().mockReturnValue({
    fetchAccounts: vi.fn(),
  }),
}));

vi.mock('@/modules/accounts/use-blockchain-accounts-api', () => ({
  useBlockchainAccounts: vi.fn().mockReturnValue({
    fetchBlockchainAccounts: vi.fn().mockResolvedValue([]),
    fetchAccounts: vi.fn().mockResolvedValue([]),
  }),
}));

vi.mock('@/composables/info/chains', async () => {
  const { computed } = await import('vue');
  const { Blockchain } = await import('@rotki/common');
  return {
    useSupportedChains: vi.fn().mockReturnValue({
      txEvmChains: computed(() => [{
        evmChainName: 'optimism',
        id: Blockchain.OPTIMISM,
        type: 'evm',
        image: '',
        name: 'Optimism',
        nativeToken: 'ETH',
      } satisfies EvmChainInfo]),
      evmAndEvmLikeTxChainsInfo: computed(() => [{
        evmChainName: 'optimism',
        id: Blockchain.OPTIMISM,
        type: 'evm',
        name: 'Optimism',
        image: '',
        nativeToken: 'ETH',
      } satisfies EvmChainInfo]),
      getChain: () => Blockchain.OPTIMISM,
      getChainName: () => Blockchain.OPTIMISM,
      getNativeAsset: (chain: Blockchain) => chain,
      isEvm: (_chain: Blockchain) => true,
    }),
  };
});

describe('useMessageHandling', () => {
  beforeAll(() => {
    const pinia = createPinia();
    setActivePinia(pinia);
  });

  it('should notify the user and run token detection', async () => {
    let messageHandling: ReturnType<typeof useMessageHandling> | undefined;

    mount({
      template: '<div/>',
      setup() {
        messageHandling = useMessageHandling();
      },
    });

    assert(messageHandling);

    const { handleMessage } = messageHandling;
    const { notify } = useNotificationDispatcher();
    const { canRequestData } = storeToRefs(useSessionAuthStore());
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

    expect(mockDetectTokens).toHaveBeenCalledTimes(1);
    expect(mockDetectTokens).toHaveBeenCalledWith('optimism', ['0xdead']);
    expect(notify).toHaveBeenCalledTimes(1);
  });
});
