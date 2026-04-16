import { Blockchain } from '@rotki/common';
import { useCsvImportExport } from '@/composables/common/use-csv-import-export';
import { useSupportedChains } from '@/composables/info/chains';
import { getAccountAddress, isXpubAccount } from '@/modules/accounts/account-utils';
import { type CSVRow, getChainType, serializeRecordToString } from '@/modules/accounts/import-export/account-csv-schema';
import { useBlockchainAccountData } from '@/modules/balances/blockchain/use-blockchain-account-data';
import { downloadFileByTextContent } from '@/modules/common/file/download';
import { useBlockchainValidatorsStore } from '@/store/blockchain/validators';

interface UseAccountExportReturn {
  exportAccounts: () => void;
}

export function useAccountExport(): UseAccountExportReturn {
  const { isEvmCompatible } = useSupportedChains();
  const { getAccounts } = useBlockchainAccountData();
  const { ethStakingValidators } = storeToRefs(useBlockchainValidatorsStore());
  const { generateCSV } = useCsvImportExport();
  const { t } = useI18n({ useScope: 'global' });

  function exportAccounts(): void {
    const rows: CSVRow[] = [];

    for (const account of getAccounts()) {
      const addressExtras: Record<string, string> = isXpubAccount(account) && account.data.derivationPath
        ? { derivationPath: account.data.derivationPath }
        : {};

      rows.push({
        address: getAccountAddress(account),
        addressExtras,
        chain: getChainType(account.chains, isEvmCompatible),
        label: account.label,
        tags: account.tags ?? [],
      });
    }

    for (const validator of get(ethStakingValidators)) {
      const ownershipPercentage = validator.ownershipPercentage;
      rows.push({
        address: validator.publicKey,
        addressExtras: ownershipPercentage ? { ownershipPercentage } : {},
        chain: Blockchain.ETH2,
        label: t('blockchain_balances.validator_index_label', { index: validator.index }),
        tags: [],
      });
    }

    const csvContent = generateCSV(rows, {
      serializers: {
        addressExtras: (value: Record<string, string>) => serializeRecordToString(value),
        tags: (value: string[]) => value.join(';'),
      },
    });

    downloadFileByTextContent(
      csvContent,
      'blockchain-accounts.csv',
      'text/csv',
    );
  }

  return {
    exportAccounts,
  };
}
