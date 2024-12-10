import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAccountImportExport } from '@/composables/accounts/use-account-import-export';
import { useBlockchainAccounts } from '@/composables/blockchain/accounts/index';
import { useTagsApi } from '@/composables/api/tags';
import { useNotificationsStore } from '@/store/notifications/index';
import { createMockCSV } from '../../../tests/unit/utils/mocks/file';
import type { Tag } from '@/types/tags';

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

vi.mock('@/composables/blockchain/accounts/index', () => {
  const mock = {
    addAccount: vi.fn().mockImplementation(async address => Promise.resolve(address)),
    addEvmAccount: vi.fn().mockImplementation(async address => Promise.resolve({
      added: {
        [address]: ['eth', 'optimism', 'gnosis'],
      },
    })),
  };
  return ({
    useBlockchainAccounts: vi.fn(() => mock),
  });
});

vi.mock('@/composables/blockchain/use-account-addition-notifications', () => ({
  useAccountAdditionNotifications: vi.fn(() => ({
    createFailureNotification: vi.fn(),
    notifyUser: vi.fn(),
  })),
}));

vi.mock('@/store/notifications', () => {
  const mock = {
    notify: vi.fn(),
  };
  return {
    useNotificationsStore: vi.fn().mockReturnValue(mock),
  };
});

describe('useAccountImportExport', () => {
  beforeEach(async () => {
    setActivePinia(createPinia());
  });

  it('should import valid accounts from csv', async () => {
    const { addAccount, addEvmAccount } = useBlockchainAccounts();
    const { queryAddTag } = useTagsApi();

    const mockFile = createMockCSV([
      'address,address extras,chain,label,tags\n'
      + '0x123,,evm,Name1,tag1;tag2\n'
      + '0x124,,eth,Name2,tag1;tag2',
    ]);

    const { importAccounts } = useAccountImportExport();
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

  it('should not import from csv with missing headers', async () => {
    const { notify } = useNotificationsStore();
    const mockFile = createMockCSV([
      'label,tags\n'
      + 'Name1,tag1;tag2\n'
      + 'Name2,tag1;tag2',
    ]);

    const { importAccounts } = useAccountImportExport();

    await expect(importAccounts(mockFile)).resolves.toBeUndefined();
    expect(notify).toHaveBeenCalledWith({
      display: true,
      message: 'blockchain_balances.import_error.invalid_format',
      title: 'blockchain_balances.import_blockchain_accounts',
    });
  });
});
