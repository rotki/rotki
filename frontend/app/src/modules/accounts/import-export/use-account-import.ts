import { Blockchain } from '@rotki/common';
import { getAccountAddress } from '@/modules/accounts/account-utils';
import { additionItem, type CSVRow, CSVSchema, doesAccountExist, getChainType, type ImportItem, trackedItem } from '@/modules/accounts/import-export/account-csv-schema';
import { useValidatorImport } from '@/modules/accounts/import-export/use-validator-import';
import { useAccountAdditionBatch } from '@/modules/accounts/use-account-addition-batch';
import { useAccountAdditions } from '@/modules/accounts/use-account-additions';
import { useBlockchainAccountManagement } from '@/modules/accounts/use-blockchain-account-management';
import { useBlockchainAccountData } from '@/modules/balances/blockchain/use-blockchain-account-data';
import { useBalancesLoading } from '@/modules/balances/use-balance-loading';
import { logger } from '@/modules/core/common/logging/logging';
import { CSVMissingHeadersError, useCsvImportExport } from '@/modules/core/common/use-csv-import-export';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { useSessionMetadataStore } from '@/modules/session/use-session-metadata-store';
import { useBlockchainValidatorsStore } from '@/modules/staking/use-blockchain-validators-store';
import { useTagOperations } from '@/modules/tags/use-tag-operations';

interface UseAccountImportReturn {
  importAccounts: (file: File) => Promise<void>;
}

export function useAccountImport(): UseAccountImportReturn {
  const { isEvmCompatible } = useSupportedChains();
  const { getAccounts } = useBlockchainAccountData();
  const { ethStakingValidators } = storeToRefs(useBlockchainValidatorsStore());
  const { addAccounts } = useBlockchainAccountManagement();
  const { reportTracked } = useAccountAdditions();
  const { runImportBatch } = useAccountAdditionBatch();
  const { attemptTagCreation } = useTagOperations();
  const { importValidators } = useValidatorImport();
  const { notifyError } = useNotifications();
  const { parseCSV } = useCsvImportExport();
  const { t } = useI18n({ useScope: 'global' });
  const { allTags } = storeToRefs(useSessionMetadataStore());

  const { loadingBlockchainBalances: blockchainLoading } = useBalancesLoading();
  const doneLoading = refDebounced(logicNot(blockchainLoading), 2000);

  /**
   * Imports parsed CSV rows as blockchain accounts, creating any tags they reference.
   *
   * @remarks
   * Resolves when every account has been added. A failing row does not abort the import or reject
   * this, so resolving means the import finished, not that every row succeeded. The dock reports
   * the outcome row by row: a row naming an account that is already tracked is sent nowhere and
   * reported as skipped, so the import accounts for every row of the file.
   *
   * Validators go last, once the account additions have settled, because both write blockchain
   * balances and the later write would be lost to a refresh already in flight.
   */
  async function handleAccountRestore(rows: CSVRow[]): Promise<void> {
    const tags: string[] = [];
    const validators: CSVRow[] = [];
    const items: ImportItem[] = [];

    const knownTags = Object.keys(get(allTags));
    const knownAccounts = getAccounts().map(group => ({
      address: getAccountAddress(group),
      chain: getChainType(group.chains, isEvmCompatible),
    })).concat(get(ethStakingValidators).map(validator => ({
      address: validator.publicKey,
      chain: Blockchain.ETH2,
    })));

    for (const row of rows) {
      if (doesAccountExist(row, knownAccounts)) {
        items.push(trackedItem(row));
        continue;
      }

      if (row.tags) {
        const missingTags = row.tags.filter(tag => !tags.includes(tag) && !knownTags.includes(tag));
        tags.push(...missingTags);
      }

      if (row.chain === Blockchain.ETH2)
        validators.push(row);
      else
        items.push(additionItem(row));
    }

    await Promise.all(tags.map(async tag => attemptTagCreation(tag)));

    const additions = items.filter(item => item.type === 'add');

    await runImportBatch(items, async (item, parent) => {
      if (item.type === 'add')
        await addAccounts(item.chain, item.account, { parent, userStarted: true, wait: true });
      else
        await reportTracked(item.chain, item.target, { parent, userStarted: true });
    });

    if (validators.length > 0) {
      if (additions.length > 0) {
        await until(blockchainLoading).toBe(true);
        await until(doneLoading).toBe(true);
      }

      await importValidators(validators);
    }
  }

  async function importAccounts(file: File): Promise<void> {
    try {
      const csvContent = await file.text();
      const accounts = CSVSchema.parse(parseCSV(csvContent, {
        requiredHeaders: ['address', 'chain'],
      }));
      await handleAccountRestore(accounts);
    }
    catch (error) {
      const message = error instanceof CSVMissingHeadersError
        ? t('blockchain_balances.import_error.invalid_format')
        : t('blockchain_balances.import_error.message', {
            error,
          });
      logger.error(message);
      notifyError(
        t('blockchain_balances.import_blockchain_accounts'),
        message,
      );
    }
  }

  return {
    importAccounts,
  };
}
