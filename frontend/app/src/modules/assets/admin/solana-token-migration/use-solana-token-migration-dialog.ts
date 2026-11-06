import type { Ref } from 'vue';
import {
  extractTargetAssetFromError,
  isUniqueConstraintError,
} from '@/modules/assets/admin/solana-token-migration/solana-migration-error';
import { useSolanaTokenMigrationApi } from '@/modules/assets/admin/solana-token-migration/solana-token-migration';
import { useSolanaTokenMigrationStore } from '@/modules/assets/admin/solana-token-migration/use-solana-token-migration-store';
import { ApiValidationError, type ValidationErrors } from '@/modules/core/api/types/errors';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { type NamedFailure, useFailureSlot } from '@/modules/shell/components/named-failure';

export interface SolanaTokenMigrationData {
  address: string;
  decimals: number | null;
  tokenKind: string;
}

export interface MergeSuggestion {
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
   * Called once the user accepts merging into the asset the migration collided with.
   *
   * @remarks
   * The collision is not an error the user can fix in this form: the target already exists, so the
   * two assets have to be merged instead. The dialog asks first, then hands the pair over and closes.
   */
  onSuggestMerge: (suggestion: MergeSuggestion) => void;
  /** Re-runs the form's own validation, so server-side errors surface on their fields. */
  validateForm: () => boolean;
}

interface UseSolanaTokenMigrationDialogReturn {
  /** Why the last migration failed where no field is to blame, named in the dialog; Migrate is the retry. */
  failure: Readonly<Ref<NamedFailure | undefined>>;
  /** The merge the dialog is asking about, after the migration collided with an existing asset. */
  mergeSuggestion: Readonly<Ref<MergeSuggestion | undefined>>;
  /** Hands the suggested merge to the caller and closes the dialog. */
  acceptMerge: () => void;
  /** Drops the question and leaves the dialog as it was. */
  dismissMerge: () => void;
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
 * existing asset into a merge question asked in the dialog.
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
  const { clear: clearFailure, failure, report } = useFailureSlot();
  const mergeSuggestion = shallowRef<MergeSuggestion>();

  const { removeIdentifier } = useSolanaTokenMigrationStore();
  const { migrateSolanaToken } = useSolanaTokenMigrationApi();

  function clearFeedback(): void {
    clearFailure();
    set(mergeSuggestion, undefined);
  }

  function clearSelection(): void {
    set(modelValue, undefined);
    set(oldAsset, undefined);
  }

  function showFieldErrors(errors: ValidationErrors): void {
    set(modelErrorMessages, errors);
    validateForm();
  }

  /** The merge a unique-constraint failure points at, or nothing when it names no asset. */
  function mergeFor(message: string, assetToMigrate: string): MergeSuggestion | undefined {
    if (!isUniqueConstraintError(message))
      return undefined;

    const targetAsset = extractTargetAssetFromError(message);
    return targetAsset ? { sourceAsset: assetToMigrate, targetAsset } : undefined;
  }

  function handleSaveException(error: unknown, assetToMigrate: string): boolean {
    const errors = error instanceof ApiValidationError ? error.getValidationErrors({}) : undefined;
    if (errors !== undefined && typeof errors !== 'string') {
      showFieldErrors(errors);
      return false;
    }

    const cause = errors ?? error;
    const suggestion = mergeFor(getErrorMessage(cause), assetToMigrate);
    if (suggestion)
      set(mergeSuggestion, suggestion);
    else
      report(t('asset_management.solana_token_migration.migration_error'), cause);
    return false;
  }

  function acceptMerge(): void {
    const suggestion = get(mergeSuggestion);
    if (!suggestion)
      return;
    onSuggestMerge(suggestion);
    clearSelection();
  }

  function dismissMerge(): void {
    set(mergeSuggestion, undefined);
  }

  async function save(): Promise<boolean> {
    if (!isDefined(modelValue) || !isDefined(oldAsset))
      return false;

    clearFeedback();

    if (!validateForm())
      return false;

    const data = get(modelValue);
    const assetToMigrate = get(oldAsset);

    if (!data.decimals) {
      showFieldErrors({ decimals: [t('asset_management.solana_token_migration.validation.decimals_non_empty')] });
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
        report(t('asset_management.solana_token_migration.dialog_title'), t('asset_management.solana_token_migration.migration_error'));
        return false;
      }

      removeIdentifier(assetToMigrate);
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

  watch(() => isDefined(modelValue), clearFeedback);

  return {
    acceptMerge,
    dismissMerge,
    failure,
    loading: readonly(loading),
    mergeSuggestion: readonly(mergeSuggestion),
    modelErrorMessages,
    save,
  };
}
