import type { ComputedRef, ModelRef, Ref } from 'vue';
import type { ValidationErrors } from '@/modules/core/api/types/errors';
import { isValidEthAddress, isValidSolanaAddress } from '@rotki/common';
import useVuelidate from '@vuelidate/core';
import { helpers, required, requiredIf } from '@vuelidate/validators';
import { useFormStateWatcher } from '@/modules/core/common/use-form';
import { toMessages } from '@/modules/core/common/validation/validation';

interface AssetFormStates {
  address: Ref<string>;
  assetType: Ref<string | null | undefined>;
  coingecko: Ref<string>;
  collectibleId: Ref<string>;
  cryptocompare: Ref<string>;
  decimals: Ref<number | null | undefined>;
  evmChain: Ref<string | null | undefined>;
  forked: Ref<string>;
  isRebasing: Ref<boolean>;
  name: Ref<string>;
  protocol: Ref<string>;
  started: Ref<number | null | undefined>;
  swappedFor: Ref<string>;
  symbol: Ref<string>;
  tokenKind: Ref<string | null | undefined>;
}

interface UseManagedAssetFormValidationOptions {
  /** Backend validation errors keyed by field, handed to Vuelidate as `$externalResults` so server messages surface on the matching input. */
  errors: Ref<ValidationErrors>;
  /** Selects the ethereum address format check for the `address` field. */
  isEvmToken: ComputedRef<boolean>;
  /** True for ERC721 token kinds, which is what makes `collectibleId` required. */
  isNft: ComputedRef<boolean>;
  /** Selects the solana address format check for the `address` field. */
  isSolanaToken: ComputedRef<boolean>;
  /** True for EVM or Solana tokens. Makes `address` required and turns on the format check. */
  isTokenRequiresAddress: ComputedRef<boolean>;
  /** The form's field refs, bound to the edited asset. Serves both as the Vuelidate state object and as the source watched for dirty tracking. */
  states: AssetFormStates;
  /** The parent dialog's model. `useFormStateWatcher` flips it to true once any field in `states` changes, so unsaved edits can be warned about. */
  stateUpdated: ModelRef<boolean>;
}

interface UseManagedAssetFormValidationReturn {
  toMessages: typeof toMessages;
  v$: ReturnType<typeof useVuelidate>;
}

export function useManagedAssetFormValidation(options: UseManagedAssetFormValidationOptions): UseManagedAssetFormValidationReturn {
  const { errors, isEvmToken, isNft, isSolanaToken, isTokenRequiresAddress, states, stateUpdated } = options;

  const { t } = useI18n({ useScope: 'global' });

  const externalServerValidation = (): boolean => true;

  const v$ = useVuelidate({
    address: {
      required: requiredIf(isTokenRequiresAddress),
      validated: helpers.withMessage(
        t('asset_form.validation.valid_address'),
        (v: string) => !get(isTokenRequiresAddress) || (get(isEvmToken) && isValidEthAddress(v)) || (get(isSolanaToken) && isValidSolanaAddress(v)),
      ),
    },
    assetType: { required },
    coingecko: { externalServerValidation },
    collectibleId: {
      required: requiredIf(isNft),
    },
    cryptocompare: { externalServerValidation },
    decimals: { externalServerValidation },
    evmChain: { externalServerValidation },
    forked: { externalServerValidation },
    name: { externalServerValidation },
    protocol: { externalServerValidation },
    started: { externalServerValidation },
    swappedFor: { externalServerValidation },
    symbol: { externalServerValidation },
    tokenKind: { externalServerValidation },
  }, states, { $autoDirty: true, $externalResults: errors });

  useFormStateWatcher(states, stateUpdated);

  return {
    toMessages,
    v$,
  };
}
