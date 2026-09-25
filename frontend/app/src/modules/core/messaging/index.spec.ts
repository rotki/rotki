import type { EvmChainInfo } from '@/modules/core/api/types/chains';
import { assert, type Blockchain } from '@rotki/common';
import { mount } from '@vue/test-utils';
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';
import { useSessionAuthStore } from '@/modules/auth/use-session-auth-store';
import { useMessageHandling } from '@/modules/core/messaging';
import { SocketMessageType } from '@/modules/core/messaging/types';
import { createNotification } from '@/modules/core/notifications/notification-utils';
import { useNotificationDispatcher } from '@/modules/core/notifications/use-notification-dispatcher';
import { useNotificationsStore } from '@/modules/core/notifications/use-notifications-store';

const { mockConsumeMessages } = vi.hoisted((): { mockConsumeMessages: ReturnType<typeof vi.fn> } => ({
  mockConsumeMessages: vi.fn(),
}));

vi.mock('@/modules/session/api/use-session-api', () => ({
  useSessionApi: vi.fn().mockReturnValue({
    consumeMessages: mockConsumeMessages,
  }),
}));

vi.mock('@shared/utils', async (importOriginal): Promise<typeof import('@shared/utils')> => {
  const actual = await importOriginal<typeof import('@shared/utils')>();
  return {
    ...actual,
    // eslint-disable-next-line @typescript-eslint/consistent-type-assertions -- the stub skips the retry delays; the generic backoff signature cannot be reproduced inline
    backoff: (async (_retries: number, call: () => Promise<unknown>) => call()) as typeof actual.backoff,
  };
});

function setup(): ReturnType<typeof useMessageHandling> {
  let messageHandling: ReturnType<typeof useMessageHandling> | undefined;
  mount({
    template: '<div/>',
    setup() {
      messageHandling = useMessageHandling();
    },
  });
  assert(messageHandling);
  return messageHandling;
}

vi.mock('@/modules/core/notifications/use-notifications-store', async () => {
  const { shallowRef } = await import('vue');
  return {
    useNotificationsStore: vi.fn().mockReturnValue({
      data: shallowRef([]),
    }),
  };
});

vi.mock('@/modules/core/notifications/use-notification-dispatcher', () => ({
  useNotificationDispatcher: vi.fn().mockReturnValue({
    notify: vi.fn(),
  }),
}));

const { mockRefreshBalances } = vi.hoisted((): { mockRefreshBalances: ReturnType<typeof vi.fn> } => ({
  mockRefreshBalances: vi.fn(),
}));
vi.mock('@/modules/balances/blockchain/use-token-detection-orchestrator', async () => {
  const { computed } = await import('vue');
  return {
    useTokenDetectionOrchestrator: vi.fn().mockReturnValue({
      detectTokens: vi.fn(),
      detectAllTokens: vi.fn(),
      useIsDetecting: vi.fn().mockReturnValue(computed(() => false)),
    }),
  };
});
vi.mock('@/modules/balances/use-blockchain-balances', () => ({
  useBlockchainBalances: vi.fn().mockReturnValue({ refreshBlockchainBalances: mockRefreshBalances }),
}));

vi.mock('@/modules/accounts/use-blockchain-account-management', () => ({
  useBlockchainAccountManagement: vi.fn().mockReturnValue({
    fetchAccounts: vi.fn(),
  }),
}));

vi.mock('@/modules/core/common/use-supported-chains', async () => {
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

  beforeEach(() => {
    vi.clearAllMocks();
    set(storeToRefs(useNotificationsStore()).data, []);
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

    expect(mockRefreshBalances).toHaveBeenCalledTimes(1);
    expect(mockRefreshBalances).toHaveBeenCalledWith(
      { blockchain: 'optimism' },
      'background',
      { detect: true, detectAddresses: ['0xdead'] },
    );
    expect(notify).toHaveBeenCalledTimes(1);
  });

  it('should ignore a message with an invalid format', async () => {
    const { handleMessage } = setup();
    const { notify } = useNotificationDispatcher();

    await handleMessage(JSON.stringify({ foo: 'bar' }));

    expect(notify).not.toHaveBeenCalled();
  });

  it('should notify once for a user message polled twice, then for the warning', async () => {
    const userError = {
      type: SocketMessageType.USER_MESSAGE,
      data: { verbosity: 'error', value: 'an error', key: 'local_db', subject: null, fields: { entry: 'tag' } },
    };
    mockConsumeMessages.mockResolvedValue({
      errors: [userError, userError],
      warnings: [{
        type: SocketMessageType.USER_MESSAGE,
        data: { verbosity: 'warning', value: 'a warning', key: 'local_db', subject: null, fields: { entry: 'tag' } },
      }],
    });

    const { consume } = setup();
    const { notify } = useNotificationDispatcher();

    await consume();

    expect(vi.mocked(notify).mock.calls.map(([n]) => n.message)).toEqual(['an error', 'a warning']);
  });

  it('should route a valid typed polling message to its handler', async () => {
    mockConsumeMessages.mockResolvedValue({
      errors: [{
        type: SocketMessageType.EVM_ACCOUNTS_DETECTION,
        data: [{ address: '0xdead', chain: 'optimism' }],
      }],
      warnings: [],
    });

    const { canRequestData } = storeToRefs(useSessionAuthStore());
    set(canRequestData, true);

    const { consume } = setup();
    const { notify } = useNotificationDispatcher();

    await consume();

    expect(mockRefreshBalances).toHaveBeenCalledWith(
      { blockchain: 'optimism' },
      'background',
      { detect: true, detectAddresses: ['0xdead'] },
    );
    expect(notify).toHaveBeenCalledTimes(1);
  });

  it('should drop a polled message that fails the schema and still show the rest', async () => {
    mockConsumeMessages.mockResolvedValue({
      errors: [
        { unexpected: true },
        { type: SocketMessageType.USER_MESSAGE, data: { verbosity: 'error', value: 'valid', key: 'local_db', subject: null, fields: { entry: 'tag' } } },
      ],
      warnings: [],
    });

    const { consume } = setup();
    const { notify } = useNotificationDispatcher();

    await consume();

    expect(vi.mocked(notify).mock.calls.map(([n]) => n.message)).toEqual(['valid']);
  });

  it('should render a polled classified user message as its value', async () => {
    mockConsumeMessages.mockResolvedValue({
      errors: [{
        type: SocketMessageType.USER_MESSAGE,
        data: {
          verbosity: 'error',
          value: 'Failed to deserialize a kucoin balance. Ignoring it.',
          key: 'bad_data',
          subject: 'kucoin',
          fields: { record: 'balance', error: 'Missing key: amount' },
        },
      }],
      warnings: [],
    });

    const { consume } = setup();
    const { notify } = useNotificationDispatcher();

    await consume();

    expect(notify).toHaveBeenCalledTimes(1);
    expect(vi.mocked(notify).mock.calls[0][0].message).toBe('Failed to deserialize a kucoin balance. Ignoring it.');
  });

  it('should skip a polled user message whose text is already a notification', async () => {
    set(storeToRefs(useNotificationsStore()).data, [createNotification(1, { message: 'already shown', title: 'backend' })]);
    mockConsumeMessages.mockResolvedValue({
      errors: [{
        type: SocketMessageType.USER_MESSAGE,
        data: { verbosity: 'error', value: 'already shown', key: 'local_db', subject: null, fields: { entry: 'tag' } },
      }],
      warnings: [],
    });

    const { consume } = setup();
    const { notify } = useNotificationDispatcher();

    await consume();

    expect(notify).not.toHaveBeenCalled();
  });

  it('should notify when message consumption fails', async () => {
    mockConsumeMessages.mockRejectedValue(new Error('network down'));

    const { consume } = setup();
    const { notify } = useNotificationDispatcher();

    await consume();

    expect(notify).toHaveBeenCalledTimes(1);
    expect(vi.mocked(notify).mock.calls[0][0].message).toContain('network down');
  });
});
