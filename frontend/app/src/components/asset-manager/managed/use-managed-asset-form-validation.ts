import type { ComputedRef, ModelRef, Ref } from 'vue';
import type { ValidationErrors } from '@/types/api/errors';
import { isValidEthAddress, isValidSolanaAddress } from '@rotki/common';
import useVuelidate from '@vuelidate/core';
import { helpers, required, requiredIf } from '@vuelidate/validators';
import { useFormStateWatcher } from '@/composables/form';
import { toMessages } from '@/utils/validation';

interface AssetFormStates {
  address: Ref<string>;
  assetType: Ref<string | null | undefined>;
  coingecko: Ref<string>;
  collectibleId: Ref<string>;
  cryptocompare: Ref<string>;
  decimals: Ref<number | null | undefined>;
  evmChain: Ref<string | null | undefined>;
  forked: Ref<string>;
  name: Ref<string>;
  protocol: Ref<string>;
  started: Ref<number | null | undefined>;
  swappedFor: Ref<string>;
  symbol: Ref<string>;
  tokenKind: Ref<string | null | undefined>;
}

interface UseManagedAssetFormValidationOptions {
  errors: Ref<ValidationErrors>;
  isEvmToken: ComputedRef<boolean>;
  isNft: ComputedRef<boolean>;
  isSolanaToken: ComputedRef<boolean>;
  isTokenRequiresAddress: ComputedRef<boolean>;
  states: AssetFormStates;
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
