import type { AddAccountsPayload, XpubAccountPayload } from '@/types/blockchain/accounts';
import { Blockchain } from '@rotki/common';
import { type StakingValidatorManage, useAccountManage } from '@/composables/accounts/blockchain/use-account-manage';
import { CSVMissingHeadersError, useCsvImportExport } from '@/composables/common/use-csv-import-export';
import { useSupportedChains } from '@/composables/info/chains';
import { useSectionStatus } from '@/composables/status';
import { createValidatorAction, type CSVRow, CSVSchema, csvToAccount, doesAccountExist, getChainType } from '@/modules/accounts/import-export/account-csv-schema';
import { useBlockchainAccountManagement } from '@/modules/accounts/use-blockchain-account-management';
import { useBlockchainAccountData } from '@/modules/balances/blockchain/use-blockchain-account-data';
import { useNotifications } from '@/modules/notifications/use-notifications';
import { useTagOperations } from '@/modules/session/use-tag-operations';
import { useBlockchainValidatorsStore } from '@/store/blockchain/validators';
import { useSessionMetadataStore } from '@/store/session/metadata';
import { useAccountImportProgressStore } from '@/store/use-account-import-progress-store';
import { Section } from '@/types/status';
import { awaitParallelExecution } from '@/utils/await-parallel-execution';
import { getAccountAddress, getXpubId } from '@/utils/blockchain/accounts/utils';
import { logger } from '@/utils/logging';
import { getKeyType, guessPrefix, isPrefixed } from '@/utils/xpub';

interface UseAccountImportReturn {
  importAccounts: (file: File) => Promise<void>;
}

export function useAccountImport(): UseAccountImportReturn {
  const { isEvmCompatible } = useSupportedChains();
  const { getAccounts } = useBlockchainAccountData();
  const { ethStakingValidators } = storeToRefs(useBlockchainValidatorsStore());
  const { addAccounts, addEvmAccounts } = useBlockchainAccountManagement();
  const { attemptTagCreation } = useTagOperations();
  const { save } = useAccountManage();
  const { notifyError, notifyInfo } = useNotifications();
  const { parseCSV } = useCsvImportExport();
  const { t } = useI18n({ useScope: 'global' });
  const { allTags } = storeToRefs(useSessionMetadataStore());
  const progressStore = useAccountImportProgressStore();
  const { increment, setTotal, skip } = progressStore;
  const { progress } = storeToRefs(progressStore);

  const { isLoading: blockchainLoading } = useSectionStatus(Section.BLOCKCHAIN);
  const doneLoading = refDebounced(logicNot(blockchainLoading), 2000);

  async function importValidators(validators: CSVRow[]): Promise<void> {
    const validatorActions: StakingValidatorManage[] = [];

    for (const validator of validators) {
      const ownershipPercentage = validator.addressExtras.ownershipPercentage || '100';
      const publicKey = validator.address;

      validatorActions.push(createValidatorAction('add', {
        ownershipPercentage,
        publicKey,
      }));
    }

    await awaitParallelExecution(
      validatorActions,
      item => item.data.publicKey!,
      async (item) => {
        increment();
        await save(item);
      },
      1,
    );
  }

  async function handleAccountRestore(rows: CSVRow[]): Promise<void> {
    const tags: string[] = [];
    const validators: CSVRow[] = [];
    const evmAccounts: AddAccountsPayload[] = [];
    const accounts: [string, string, AddAccountsPayload | XpubAccountPayload][] = [];

    const knownTags = Object.keys(get(allTags));
    const knownAccounts = getAccounts().map(group => ({
      address: getAccountAddress(group),
      chain: getChainType(group.chains, isEvmCompatible),
    })).concat(get(ethStakingValidators).map(validator => ({
      address: validator.publicKey,
      chain: Blockchain.ETH2,
    })));

    setTotal(rows.length);

    for (const row of rows) {
      if (doesAccountExist(row, knownAccounts)) {
        skip();
        continue;
      }

      if (row.tags) {
        const missingTags = row.tags.filter(tag => !tags.includes(tag) && !knownTags.includes(tag));
        tags.push(...missingTags);
      }

      if (row.chain === 'evm') {
        evmAccounts.push({ payload: [csvToAccount(row)] });
      }
      else if (row.chain === Blockchain.ETH2) {
        validators.push(row);
      }
      else if (isPrefixed(row.address)) {
        const xpub: XpubAccountPayload = {
          label: row.label,
          tags: row.tags,
          xpub: {
            derivationPath: row.addressExtras.derivationPath,
            xpub: row.address,
            xpubType: getKeyType(guessPrefix(row.address)),
          },
        };
        const xpubId = getXpubId(xpub.xpub);
        accounts.push([row.chain, xpubId, xpub] as const);
      }
      else {
        accounts.push([row.chain, row.address, { payload: [csvToAccount(row)] }] as const);
      }
    }

    await Promise.all(tags.map(async tag => attemptTagCreation(tag)));

    await awaitParallelExecution(
      evmAccounts,
      accounts => accounts.payload[0].address,
      async (payload) => {
        increment();
        await addEvmAccounts(payload, { wait: true });
      },
      1,
    );

    await awaitParallelExecution(
      accounts,
      ([_chain, id]) => id,
      async ([chain, _id, account]) => {
        increment();
        try {
          await addAccounts(chain, account, { wait: true });
        }
        catch (error) {
          logger.error(error);
        }
      },
      1,
    );

    if (validators.length > 0) {
      // Wait until accounts refreshed
      if (evmAccounts.length > 0 || accounts.length > 0) {
        await until(blockchainLoading).toBe(true);
        await until(doneLoading).toBe(true);
      }

      await importValidators(validators);
    }

    const { skipped, total } = get(progress);

    notifyInfo(
      t('blockchain_balances.import_blockchain_accounts'),
      t('blockchain_balances.import_blockchain_accounts_complete', {
        imported: total - skipped,
        skipped,
        total,
      }),
    );

    setTotal(0);
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
