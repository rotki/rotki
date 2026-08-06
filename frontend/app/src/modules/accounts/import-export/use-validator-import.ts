import { type StakingValidatorManage, useAccountManage } from '@/modules/accounts/blockchain/use-account-manage';
import { createValidatorAction, type CSVRow } from '@/modules/accounts/import-export/account-csv-schema';
import { awaitParallelExecution } from '@/modules/core/common/async/await-parallel-execution';

interface UseValidatorImportReturn {
  importValidators: (validators: CSVRow[], onProgress: () => void) => Promise<void>;
}

/**
 * Validators are imported through the account form's `save`, not through the account addition
 * mechanism, so they keep their own serial loop rather than joining the import umbrella. Folding
 * them in would mean routing validator creation through `addAccounts`, which is a different change.
 */
export function useValidatorImport(): UseValidatorImportReturn {
  const { save } = useAccountManage();

  const importValidators = async (validators: CSVRow[], onProgress: () => void): Promise<void> => {
    const validatorActions: StakingValidatorManage[] = validators.map((validator) => {
      const ownershipPercentage = validator.addressExtras.ownershipPercentage || '100';
      return createValidatorAction('add', {
        ownershipPercentage,
        publicKey: validator.address,
      });
    });

    await awaitParallelExecution(
      validatorActions,
      item => item.data.publicKey!,
      async (item) => {
        onProgress();
        await save(item);
      },
      1,
    );
  };

  return { importValidators };
}
