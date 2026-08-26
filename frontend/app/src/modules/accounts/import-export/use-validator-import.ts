import { type StakingValidatorManage, useAccountManage } from '@/modules/accounts/blockchain/use-account-manage';
import { createValidatorAction, type CSVRow } from '@/modules/accounts/import-export/account-csv-schema';

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

  /**
   * Adds every validator in an import, one at a time.
   *
   * @remarks
   * Serial on purpose, and not a candidate for parallelising. The backend checks
   * `validator_exists` in its own read cursor and inserts in a later write cursor, with
   * beaconcha.in calls in between, so two concurrent adds of one key can both pass the check. A
   * file listing the same validator twice is exactly that case, and every row is attempted.
   */
  const importValidators = async (validators: CSVRow[], onProgress: () => void): Promise<void> => {
    const validatorActions: StakingValidatorManage[] = validators.map((validator) => {
      const ownershipPercentage = validator.addressExtras.ownershipPercentage || '100';
      return createValidatorAction('add', {
        ownershipPercentage,
        publicKey: validator.address,
      });
    });

    for (const item of validatorActions) {
      await save(item);
      onProgress();
    }
  };

  return { importValidators };
}
