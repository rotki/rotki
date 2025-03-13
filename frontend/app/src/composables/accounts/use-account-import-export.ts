import { z } from 'zod';
import { Severity } from '@rotki/common';
import { useSupportedChains } from '@/composables/info/chains';
import { awaitParallelExecution } from '@/utils/await-parallel-execution';
import { type StakingValidatorManage, useAccountManage } from '@/composables/accounts/blockchain/use-account-manage';
import { getAccountAddress, getXpubId } from '@/utils/blockchain/accounts/utils';
import { downloadFileByTextContent } from '@/utils/download';
import { useBlockchainStore } from '@/store/blockchain/index';
import { useBlockchains } from '@/composables/blockchain/index';
import { useTagStore } from '@/store/session/tags';
import { useStatusStore } from '@/store/status';
import { useNotificationsStore } from '@/store/notifications/index';
import { Section } from '@/types/status';
import { CSVMissingHeadersError, useCsvImportExport } from '@/composables/common/use-csv-import-export';
import { logger } from '@/utils/logging';
import { useBlockchainValidatorsStore } from '@/store/blockchain/validators';
import { getKeyType, guessPrefix, isPrefixed } from '@/utils/xpub';
import { useAccountImportProgressStore } from '@/store/use-account-import-progress-store';
import type { AccountPayload, AddAccountsPayload, XpubAccountPayload } from '@/types/blockchain/accounts';
import type { Eth2Validator } from '@/types/balances';

const CSVRow = z.object({
  address: z.string(),
  addressExtras: z.string().transform(value => serializedStringToRecord(value)),
  chain: z.string(),
  label: z.string().optional(),
  tags: z.string().optional().transform(value => value ? value.split(';') : []),
});

const CSVSchema = z.array(CSVRow);

type CSVRow = z.infer<typeof CSVRow>;

interface UseAccountImportExportReturn {
  exportAccounts: () => void;
  importAccounts: (file: File) => Promise<void>;
}

function serializedStringToRecord(serialized: string): Record<string, string> {
  const record: Record<string, string> = {};
  serialized.split('&').forEach((pair) => {
    const [key, value] = pair.split('=');
    if (key) {
      record[key] = value || '';
    }
  });

  return record;
}

function serializeRecordToString(record: Record<string, string>): string {
  return Object.entries(record)
    .map(([key, value]) => `${key}=${value}`)
    .join('&');
}

function createValidatorAction(mode: 'add' | 'edit', data: Eth2Validator): StakingValidatorManage {
  return {
    chain: Blockchain.ETH2,
    data,
    mode,
    type: 'validator',
  };
}

function doesAccountExist(row: CSVRow, accounts: { address: string; chain: string }[]): boolean {
  return accounts.some(account => account.chain === row.chain && account.address === row.address);
}

export function useAccountImportExport(): UseAccountImportExportReturn {
  const { isEvm, isEvmLikeChains } = useSupportedChains();
  const { groups } = storeToRefs(useBlockchainStore());
  const { ethStakingValidators } = storeToRefs(useBlockchainValidatorsStore());
  const { addAccounts, addEvmAccounts } = useBlockchains();
  const { attemptTagCreation } = useTagStore();
  const { isLoading } = useStatusStore();
  const { save } = useAccountManage();
  const { notify } = useNotificationsStore();
  const { generateCSV, parseCSV } = useCsvImportExport();
  const { t } = useI18n();
  const { allTags } = useTagStore();
  const progressStore = useAccountImportProgressStore();
  const { increment, setTotal, skip } = progressStore;
  const { progress } = storeToRefs(progressStore);

  const blockchainLoading = isLoading(Section.BLOCKCHAIN);
  const blockchainLoadingDebounced = refDebounced(blockchainLoading, 2000);
  const doneLoading = logicAnd(logicNot(blockchainLoading), logicNot(blockchainLoadingDebounced));

  const csvToAccount = (acc: CSVRow): AccountPayload => ({
    address: acc.address,
    label: acc.label,
    tags: acc.tags || null,
  });

  function getChainType(chains: string[]): string {
    const EVM_CHAIN_TYPE = 'evm';
    const hasEvmSupport = (chain: string): boolean => get(isEvm(chain)) || get(isEvmLikeChains(chain));

    if (chains.length > 1 && chains.some(hasEvmSupport)) {
      return EVM_CHAIN_TYPE;
    }
    else {
      return chains[0];
    }
  }

  function exportAccounts(): void {
    const rows: CSVRow[] = [];

    for (const group of get(groups)) {
      const addressExtras: Record<string, string> = group.data.type === 'xpub' && group.data.derivationPath
        ? { derivationPath: group.data.derivationPath }
        : {};

      rows.push({
        address: getAccountAddress(group),
        addressExtras,
        chain: getChainType(group.chains),
        label: group.label,
        tags: group.tags ?? [],
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

    const knownTags = Object.keys(allTags);
    const knownAccounts = get(groups).map(group => ({
      address: getAccountAddress(group),
      chain: getChainType(group.chains),
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

    notify({
      display: true,
      message: t('blockchain_balances.import_blockchain_accounts_complete', {
        imported: total - skipped,
        skipped,
        total,
      }),
      severity: Severity.INFO,
      title: t('blockchain_balances.import_blockchain_accounts'),
    });

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
      notify({
        display: true,
        message,
        title: t('blockchain_balances.import_blockchain_accounts'),
      });
    }
  }

  return {
    exportAccounts,
    importAccounts,
  };
}
