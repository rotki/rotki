import type { Ref } from 'vue';
import {
  extractTargetAssetFromError,
  isUniqueConstraintError,
} from '@/modules/assets/admin/solana-token-migration/solana-migration-error';
import { useSolanaTokenMigrationApi } from '@/modules/assets/admin/solana-token-migration/solana-token-migration';
import { useSolanaTokenMigrationStore } from '@/modules/assets/admin/solana-token-migration/use-solana-token-migration-store';
import { ApiValidationError, type ValidationErrors } from '@/modules/core/api/types/errors';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useMessageStore } from '@/modules/core/common/use-message-store';

export interface SolanaTokenMigrationData {
  address: string;
  decimals: number | null;
  tokenKind: string;
}

interface MergeSuggestion {
  sourceAsset: string;
  targetAsset: string;
}

interface UseSolanaTokenMigrationDialogOptions {
  /** The token being migrated to, cleared once the migration lands or is handed to a merge. */
  modelValue: Ref<SolanaTokenMigrationData | undefined>;
  /** The asset being migrated from. */
  oldAsset: Ref<string | undefined>;
  /** Called after a successful migration, so the caller can refresh its list. */
  onMigrated: () => void;
  /**
   * Called when the migration collided with an asset that already exists.
   *
   * @remarks
   * The collision is not an error the user can fix in this form: the target already exists, so the
   * two assets have to be merged instead. The dialog hands the pair over and closes.
   */
  onSuggestMerge: (suggestion: MergeSuggestion) => void;
  /** Re-runs the form's own validation, so server-side errors surface on their fields. */
  validateForm: () => boolean;
}

interface UseSolanaTokenMigrationDialogReturn {
  /** Field errors returned by the server. */
  modelErrorMessages: Ref<ValidationErrors>;
  /** Whether the migration is in flight. */
  loading: Readonly<Ref<boolean>>;
  /**
   * Migrates the asset.
   *
   * @returns whether the migration landed; `false` leaves the dialog open with the reason shown
   */
  save: () => Promise<boolean>;
}

/**
 * Drives the Solana token migration dialog: validating, migrating, and turning a collision with an
 * existing asset into a merge suggestion.
 *
 * @returns the dialog's state and its submit
 */
export function useSolanaTokenMigrationDialog(
  options: UseSolanaTokenMigrationDialogOptions,
): UseSolanaTokenMigrationDialogReturn {
  const { modelValue, oldAsset, onMigrated, onSuggestMerge, validateForm } = options;

  const { t } = useI18n({ useScope: 'global' });

  const modelErrorMessages = ref<ValidationErrors>({});
  const loading = shallowRef<boolean>(false);

  const { setMessage } = useMessageStore();
  const { removeIdentifier } = useSolanaTokenMigrationStore();
  const { migrateSolanaToken } = useSolanaTokenMigrationApi();

  function report(description: string, title: string): void {
    setMessage({ description, title });
  }

  function clearSelection(): void {
    set(modelValue, undefined);
    set(oldAsset, undefined);
  }

  function suggestMergeOnConflict(message: string, assetToMigrate: string): boolean {
    if (!isUniqueConstraintError(message))
      return false;

    const targetAsset = extractTargetAssetFromError(message);
    if (!targetAsset)
      return false;

    onSuggestMerge({ sourceAsset: assetToMigrate, targetAsset });
    clearSelection();
    return true;
  }

  function handleSaveException(error: unknown, assetToMigrate: string): boolean {
    let errors: ValidationErrors | string = getErrorMessage(error);
    if (error instanceof ApiValidationError)
      errors = error.getValidationErrors({});

    if (typeof errors === 'string') {
      if (suggestMergeOnConflict(errors, assetToMigrate))
        return false;

      report(errors, t('asset_management.solana_token_migration.migration_error'));
    }
    else {
      set(modelErrorMessages, errors);
      validateForm();
    }
    return false;
  }

  async function save(): Promise<boolean> {
    if (!isDefined(modelValue) || !isDefined(oldAsset))
      return false;

    if (!validateForm())
      return false;

    const data = get(modelValue);
    const assetToMigrate = get(oldAsset);

    if (!data.decimals || !assetToMigrate) {
      report(
        t('asset_management.solana_token_migration.validation_error'),
        t('asset_management.solana_token_migration.dialog_title'),
      );
      return false;
    }

    set(loading, true);

    try {
      const result = await migrateSolanaToken({
        address: data.address,
        decimals: data.decimals,
        oldAsset: assetToMigrate,
        tokenKind: data.tokenKind,
      });

      if (!result) {
        report(
          t('asset_management.solana_token_migration.migration_error'),
          t('asset_management.solana_token_migration.dialog_title'),
        );
        return false;
      }

      removeIdentifier(assetToMigrate);
      setMessage({
        description: t('asset_management.solana_token_migration.migration_success'),
        success: true,
        title: t('asset_management.solana_token_migration.dialog_title'),
      });

      clearSelection();
      onMigrated();
      return true;
    }
    catch (error: unknown) {
      return handleSaveException(error, assetToMigrate);
    }
    finally {
      set(loading, false);
    }
  }

  return {
    loading: readonly(loading),
    modelErrorMessages,
    save,
  };
}
