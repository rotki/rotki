import type { AddAccountsPayload, XpubAccountPayload } from '@/modules/accounts/blockchain-accounts';
import { Blockchain } from '@rotki/common';
import { getAccountAddress, getXpubId } from '@/modules/accounts/account-utils';
import { EVM_PSEUDO_CHAIN } from '@/modules/accounts/accounts.activity';
import { type CSVRow, CSVSchema, csvToAccount, doesAccountExist, getChainType } from '@/modules/accounts/import-export/account-csv-schema';
import { useValidatorImport } from '@/modules/accounts/import-export/use-validator-import';
import { useAccountAdditionBatch } from '@/modules/accounts/use-account-addition-batch';
import { useAccountImportProgressStore } from '@/modules/accounts/use-account-import-progress-store';
import { useBlockchainAccountManagement } from '@/modules/accounts/use-blockchain-account-management';
import { getKeyType, guessPrefix, isPrefixed } from '@/modules/accounts/xpub';
import { useBlockchainAccountData } from '@/modules/balances/blockchain/use-blockchain-account-data';
import { logger } from '@/modules/core/common/logging/logging';
import { CSVMissingHeadersError, useCsvImportExport } from '@/modules/core/common/use-csv-import-export';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { useSessionMetadataStore } from '@/modules/session/use-session-metadata-store';
import { useBlockchainValidatorsStore } from '@/modules/staking/use-blockchain-validators-store';
import { useTagOperations } from '@/modules/tags/use-tag-operations';
import { ActivityKind } from '@/modules/task-center/core/types';
import { useTaskCenter } from '@/modules/task-center/use-task-center';

interface UseAccountImportReturn {
  importAccounts: (file: File) => Promise<void>;
}

export function useAccountImport(): UseAccountImportReturn {
  const { isEvmCompatible } = useSupportedChains();
  const { getAccounts } = useBlockchainAccountData();
  const { ethStakingValidators } = storeToRefs(useBlockchainValidatorsStore());
  const { addAccounts } = useBlockchainAccountManagement();
  const { runImportBatch } = useAccountAdditionBatch();
  const { attemptTagCreation } = useTagOperations();
  const { importValidators } = useValidatorImport();
  const { notifyError, notifyInfo } = useNotifications();
  const { parseCSV } = useCsvImportExport();
  const { t } = useI18n({ useScope: 'global' });
  const { allTags } = storeToRefs(useSessionMetadataStore());
  const progressStore = useAccountImportProgressStore();
  const { increment, setTotal, skip } = progressStore;
  const { progress } = storeToRefs(progressStore);

  const { useIsActive } = useTaskCenter();
  const blockchainLoading = useIsActive(ActivityKind.BLOCKCHAIN_BALANCES);
  const doneLoading = refDebounced(logicNot(blockchainLoading), 2000);

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

    // One umbrella for the whole import, and no limiter of its own: every row's addition already
    // submits onto `accounts-add:<chain>`, capped at 2 per chain with 2 chains live, so a second
    // mechanism here would be the trap documented on `DECODE_LANE` one layer up.
    //
    // ⚠️ This is a deliberate behaviour change: rows used to run strictly one at a time.
    const additions = [
      ...evmAccounts.map(payload => [EVM_PSEUDO_CHAIN, payload] as const),
      ...accounts.map(([chain, _id, account]) => [chain, account] as const),
    ];

    await runImportBatch(
      additions,
      async ([chain, account], parent) => {
        // Both kinds of row take the same call with the same contract. The EVM loop previously had
        // no `try/catch` while the chain one did, so a failed EVM row aborted the whole import and
        // a failed chain row did not — accidental, not chosen. Neither throws now.
        await addAccounts(chain, account, { parent, wait: true });
        // Counted after the row lands, not before. The batch starts every row's callback in the
        // same tick, so incrementing first drove the bar to 100% before a single account had been
        // submitted and left it parked there while the lanes drained.
        increment();
      },
    );

    if (validators.length > 0) {
      // Wait until accounts refreshed
      if (evmAccounts.length > 0 || accounts.length > 0) {
        await until(blockchainLoading).toBe(true);
        await until(doneLoading).toBe(true);
      }

      await importValidators(validators, increment);
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
