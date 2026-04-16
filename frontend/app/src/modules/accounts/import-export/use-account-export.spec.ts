import { Blockchain } from '@rotki/common';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createAccount, createValidatorAccount } from '@/modules/accounts/create-account';
import { useAccountExport } from '@/modules/accounts/import-export/use-account-export';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { downloadFileByTextContent } from '@/modules/common/file/download';

const VALIDATOR_1 = '0xa685b19738ac8d7ee301f434f77fdbca50f7a2b8d287f4ab6f75cae251aa821576262b79ae9d58d9b458ba748968dfda';
const VALIDATOR_2 = '0x8e31e6d9771094182a70b75882f7d186986d726f7b4da95f542d18a1cb7fa38cd31b450a9fc62867d81dfc9ad9cbd641';

const INDEX_1 = 507258;
const INDEX_2 = 512123;

vi.mock('@/modules/common/file/download', () => ({
  downloadFileByTextContent: vi.fn(),
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

describe('useAccountExport', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it('should export accounts', () => {
    const { updateAccounts } = useBlockchainAccountsStore();

    const tags = ['tag1', 'tag2'];

    const account = {
      address: '0x123',
      label: 'Name1',
      tags,
    };

    const secondAccount = {
      address: '0x124',
      label: 'Name2',
      tags,
    };

    const chainInfo = {
      chain: Blockchain.ETH,
      nativeAsset: 'ETH',
    };

    updateAccounts(Blockchain.ETH, [
      createAccount(account, chainInfo),
      createAccount(secondAccount, chainInfo),
    ]);

    updateAccounts(Blockchain.OPTIMISM, [
      createAccount(account, {
        chain: Blockchain.OPTIMISM,
        nativeAsset: 'ETH',
      }),
    ]);

    const { exportAccounts } = useAccountExport();
    exportAccounts();

    expect(downloadFileByTextContent).toHaveBeenCalledOnce();
    expect(downloadFileByTextContent).toHaveBeenCalledWith(
      [
        'address,address extras,chain,label,tags',
        '0x123,,evm,Name1,tag1;tag2',
        '0x124,,eth,Name2,tag1;tag2',
      ].join('\n'),
      'blockchain-accounts.csv',
      'text/csv',
    );
  });

  it('should export validators', () => {
    const { updateAccounts } = useBlockchainAccountsStore();

    const chainInfo = {
      chain: Blockchain.ETH2,
      nativeAsset: 'ETH',
    };

    updateAccounts(Blockchain.ETH2, [
      createValidatorAccount({
        index: INDEX_1,
        ownershipPercentage: '22',
        publicKey: VALIDATOR_1,
        status: 'active',
      }, chainInfo),
      createValidatorAccount({
        index: INDEX_2,
        ownershipPercentage: '44',
        publicKey: VALIDATOR_2,
        status: 'exited',
      }, chainInfo),
    ]);

    const { exportAccounts } = useAccountExport();
    exportAccounts();

    expect(downloadFileByTextContent).toHaveBeenCalledOnce();
    expect(downloadFileByTextContent).toHaveBeenCalledWith(
      [
        'address,address extras,chain,label,tags',
        `${VALIDATOR_1},ownershipPercentage=22,eth2,blockchain_balances.validator_index_label::${INDEX_1},`,
        `${VALIDATOR_2},ownershipPercentage=44,eth2,blockchain_balances.validator_index_label::${INDEX_2},`,
      ].join('\n'),
      'blockchain-accounts.csv',
      'text/csv',
    );
  });
});
