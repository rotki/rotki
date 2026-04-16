import type { AccountPayload, XpubAccountPayload } from '@/modules/accounts/blockchain-accounts';
import type { Tag } from '@/modules/tags/tags';
import { Blockchain } from '@rotki/common';
import { createMockCSV } from '@test/mocks/file';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useAccountManage } from '@/composables/accounts/blockchain/use-account-manage';
import { useTagsApi } from '@/composables/api/tags';
import { createValidatorAccount } from '@/modules/accounts/create-account';
import { useAccountImport } from '@/modules/accounts/import-export/use-account-import';
import { useBlockchainAccounts } from '@/modules/accounts/use-blockchain-accounts-api';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';

const VALIDATOR_1 = '0xa685b19738ac8d7ee301f434f77fdbca50f7a2b8d287f4ab6f75cae251aa821576262b79ae9d58d9b458ba748968dfda';
const VALIDATOR_2 = '0x8e31e6d9771094182a70b75882f7d186986d726f7b4da95f542d18a1cb7fa38cd31b450a9fc62867d81dfc9ad9cbd641';

const XPUB = 'xpub6BgBgsespWvERF3LHQu6CnqdvfEvtMcQjYrcRzx53QJjSxarj2afYWcLteoGVky7D3UKDP9QyrLprQ3VCECoY49yfdDEHGCtMMj92pReUsQ';
const DERIVATION_PATH = 'm/86/0/0';

vi.mock('@/composables/api/tags', async () => {
  const { ref } = await import('vue');
  const { get, set } = await import('@vueuse/core');

  const tags = ref<Tag[]>([]);

  const mock = {
    queryAddTag: vi.fn().mockImplementation(async (tag) => {
      set(tags, [...get(tags), tag]);
      return Promise.resolve(get(tags));
    }),
    queryTags: vi.fn().mockResolvedValue(tags),
  };

  return {
    useTagsApi: vi.fn(() => mock),
  };
});

function mockAddAccount(failOnAddress?: string[]): (_chain: string, payload: AccountPayload[] | XpubAccountPayload) => Promise<string> {
  return async (_chain, payload) => {
    if (Array.isArray(payload)) {
      if (failOnAddress && payload.length === 1 && failOnAddress.includes(payload[0].address)) {
        throw new Error(`Failed to add account: ${payload[0].address}`);
      }
      else {
        return payload[0].address;
      }
    }
    else {
      return Promise.resolve(payload.xpub.xpub);
    }
  };
}

vi.mock('@/modules/accounts/use-blockchain-accounts-api', () => {
  const mock = {
    addAccount: vi.fn().mockImplementation(mockAddAccount()),
    addEvmAccount: vi.fn().mockImplementation(async (address: string) => Promise.resolve({
      added: {
        [address]: ['eth', 'optimism', 'gnosis'],
      },
    })),
    fetch: vi.fn().mockResolvedValue(undefined),
  };
  return {
    useBlockchainAccounts: vi.fn(() => mock),
  };
});

vi.mock('@/composables/accounts/blockchain/use-account-manage', () => {
  const mock = {
    save: vi.fn().mockResolvedValue(true),
  };

  return {
    useAccountManage: vi.fn(() => mock),
  };
});

vi.mock('@/modules/accounts/use-account-addition-notifications', () => ({
  useAccountAdditionNotifications: vi.fn(() => ({
    createFailureNotification: vi.fn(),
    notifyUser: vi.fn(),
  })),
}));

const mockNotifyError = vi.fn();
const mockNotifyInfo = vi.fn();

vi.mock('@/modules/notifications/use-notifications', () => ({
  useNotifications: vi.fn((): { notifyError: typeof mockNotifyError; notifyInfo: typeof mockNotifyInfo } => ({
    notifyError: mockNotifyError,
    notifyInfo: mockNotifyInfo,
  })),
}));

vi.mock('@/composables/info/chains', async () => {
  const { useSupportedChains } = await import('@/composables/info/chains');

  const evmCompatibleChains = new Set(['eth', 'optimism']);

  return {
    useSupportedChains: vi.fn(() => ({
      ...useSupportedChains(),
      isEvm: vi.fn().mockImplementation((chain: string): boolean => evmCompatibleChains.has(chain)),
      isEvmCompatible: vi.fn().mockImplementation((chain: string): boolean => evmCompatibleChains.has(chain)),
    })),
  };
});

describe('useAccountImport', () => {
  let scope: ReturnType<typeof effectScope>;

  beforeEach(() => {
    setActivePinia(createPinia());
    scope = effectScope();
    vi.clearAllMocks();
  });

  afterEach(() => {
    scope.stop();
  });

  it('should import valid accounts from csv', async () => {
    const { addAccount, addEvmAccount } = useBlockchainAccounts();
    const { queryAddTag } = useTagsApi();

    const mockFile = createMockCSV([
      'address,address extras,chain,label,tags',
      '0x123,,evm,Name1,tag1;tag2',
      '0x124,,eth,Name2,tag1;tag2',
    ]);

    const { importAccounts } = scope.run(() => useAccountImport())!;
    await importAccounts(mockFile);

    expect(addAccount).toHaveBeenCalledTimes(1);
    expect(addAccount).toHaveBeenCalledWith('eth', [{
      address: '0x124',
      label: 'Name2',
      tags: ['tag1', 'tag2'],
    }]);
    expect(addEvmAccount).toHaveBeenCalledTimes(1);
    expect(addEvmAccount).toHaveBeenCalledWith({
      address: '0x123',
      label: 'Name1',
      tags: ['tag1', 'tag2'],
    });
    expect(queryAddTag).toHaveBeenCalledTimes(2);
    expect(queryAddTag).toHaveBeenCalledWith(expect.objectContaining({ name: 'tag1' }));
    expect(queryAddTag).toHaveBeenCalledWith(expect.objectContaining({ name: 'tag2' }));
  });

  it('should not fail to import accounts if one addition fails', async () => {
    const { addAccount, addEvmAccount } = useBlockchainAccounts();
    const { queryAddTag } = useTagsApi();

    vi.mocked(addAccount).mockImplementation(mockAddAccount(['0x124']));

    const mockFile = createMockCSV([
      'address,address extras,chain,label,tags',
      '0x123,,evm,Name1,tag1;tag2',
      '0x124,,eth,Name2,tag1;tag2',
      '0x125,,gnosis,Name3,tag1;tag2',
    ]);

    const { importAccounts } = scope.run(() => useAccountImport())!;
    await importAccounts(mockFile);

    expect(addAccount).toHaveBeenCalledTimes(2);
    expect(addAccount).toHaveBeenCalledWith('gnosis', [{
      address: '0x125',
      label: 'Name3',
      tags: ['tag1', 'tag2'],
    }]);
    expect(addEvmAccount).toHaveBeenCalledTimes(1);
    expect(addEvmAccount).toHaveBeenCalledWith({
      address: '0x123',
      label: 'Name1',
      tags: ['tag1', 'tag2'],
    });
    expect(queryAddTag).toHaveBeenCalledTimes(2);
    expect(queryAddTag).toHaveBeenCalledWith(expect.objectContaining({ name: 'tag1' }));
    expect(queryAddTag).toHaveBeenCalledWith(expect.objectContaining({ name: 'tag2' }));
  });

  it('should not import from csv with missing headers', async () => {
    const mockFile = createMockCSV([
      'label,tags',
      'Name1,tag1;tag2',
      'Name2,tag1;tag2',
    ]);

    const { importAccounts } = scope.run(() => useAccountImport())!;

    await expect(importAccounts(mockFile)).resolves.toBeUndefined();
    expect(mockNotifyError).toHaveBeenCalledWith(
      'blockchain_balances.import_blockchain_accounts',
      'blockchain_balances.import_error.invalid_format',
    );
  });

  it('should import an xpub address', async () => {
    const { addAccount } = useBlockchainAccounts();
    const { queryAddTag } = useTagsApi();

    const mockFile = createMockCSV([
      'address,address extras,chain,label,tags',
      `${XPUB},derivationPath=${DERIVATION_PATH},btc,Test Pub,tag1`,
    ]);

    const { importAccounts } = scope.run(() => useAccountImport())!;
    await importAccounts(mockFile);

    expect(addAccount).toHaveBeenCalledTimes(1);
    expect(addAccount).toHaveBeenCalledWith('btc', {
      label: 'Test Pub',
      tags: ['tag1'],
      xpub: {
        derivationPath: DERIVATION_PATH,
        xpub: XPUB,
        xpubType: 'p2pkh',
      },
    });

    expect(queryAddTag).toHaveBeenCalledTimes(1);
    expect(queryAddTag).toHaveBeenCalledWith(expect.objectContaining({ name: 'tag1' }));
  });

  it('should import validators', async () => {
    const { save } = useAccountManage();

    const mockFile = createMockCSV([
      'address,address extras,chain,label,tags',
      `${VALIDATOR_1},ownershipPercentage=80,eth2,,`,
    ]);

    const { importAccounts } = scope.run(() => useAccountImport())!;
    await importAccounts(mockFile);

    expect(save).toHaveBeenCalledTimes(1);
    expect(save).toHaveBeenCalledWith({
      chain: 'eth2',
      data: {
        ownershipPercentage: '80',
        publicKey: VALIDATOR_1,
      },
      mode: 'add',
      type: 'validator',
    });
  });

  it('should skip a validator if it is already present', async () => {
    const { save } = useAccountManage();
    const { updateAccounts } = useBlockchainAccountsStore();
    updateAccounts(Blockchain.ETH2, [
      createValidatorAccount({
        index: 55751,
        ownershipPercentage: '44',
        publicKey: VALIDATOR_2,
        status: 'exited',
      }, {
        chain: Blockchain.ETH2,
        nativeAsset: 'ETH',
      }),
    ]);

    const mockFile = createMockCSV([
      'address,address extras,chain,label,tags',
      `${VALIDATOR_1},ownershipPercentage=80,eth2,,`,
      `${VALIDATOR_2},ownershipPercentage=99,eth2,,`,
    ]);

    const { importAccounts } = scope.run(() => useAccountImport())!;
    await importAccounts(mockFile);

    expect(save).toHaveBeenCalledTimes(1);
    expect(save).toHaveBeenCalledWith({
      chain: 'eth2',
      data: {
        ownershipPercentage: '80',
        publicKey: VALIDATOR_1,
      },
      mode: 'add',
      type: 'validator',
    });
  });
});
