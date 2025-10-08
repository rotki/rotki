import type { ValidationRuleCollection, ValidationRuleWithoutParams } from '@vuelidate/core';
import type { Ref } from 'vue';
import { isValidEthAddress, isValidEvmTxHash, isValidSolanaAddress, isValidSolanaSignature } from '@rotki/common';
import { helpers, minLength, required, requiredIf } from '@vuelidate/validators';

interface CreateCommonRules {
  createExternalValidationRule: <T>() => ValidationRuleCollection<T>;
  createRequiredAmountRule: <T>() => ValidationRuleCollection<T>;
  createRequiredAssetRule: <T>() => ValidationRuleCollection<T>;
  createRequiredBlockNumberRule: <T>() => ValidationRuleCollection<T>;
  createRequiredEventIdentifierRule: <T>(condition?: () => boolean) => ValidationRuleCollection<T>;
  createRequiredEventSubtypeRule: <T>() => ValidationRuleCollection<T>;
  createRequiredEventTypeRule: <T>() => ValidationRuleCollection<T>;
  createRequiredFeeAssetRule: <T>(requiredCondition?: ValidationRuleWithoutParams) => ValidationRuleCollection<T>;
  createRequiredFeeRule: <T>(requiredCondition?: ValidationRuleWithoutParams) => ValidationRuleCollection<T>;
  createRequiredLocationRule: <T>() => ValidationRuleCollection<T>;
  createRequiredSequenceIndexRule: <T>() => ValidationRuleCollection<T>;
  createRequiredValidatorIndexRule: <T>() => ValidationRuleCollection<T>;
  createRequiredValidDepositorRule: <T>() => ValidationRuleCollection<T>;
  createRequiredValidFeeRecipientRule: <T>() => ValidationRuleCollection<T>;
  createRequiredValidWithdrawalAddressRule: <T>() => ValidationRuleCollection<T>;
  createRequiredAtLeastOne: <T>() => ValidationRuleCollection<T>;
  createValidCounterpartyRule: <T>(counterparties: Ref<string[]>) => ValidationRuleCollection<T>;
  createValidEthAddressRule: <T>() => ValidationRuleCollection<T>;
  createValidSolanaAddressRule: <T>() => ValidationRuleCollection<T>;
  createValidProductRule: <T>(products: Ref<string[]>) => ValidationRuleCollection<T>;
  createValidTxHashRule: <T>() => ValidationRuleCollection<T>;
  createValidSolanaSignatureRule: <T>() => ValidationRuleCollection<T>;
}

interface UseEventFormValidationReturn {
  createCommonRules: () => CreateCommonRules;
}

export function useEventFormValidation(): UseEventFormValidationReturn {
  const { t } = useI18n({ useScope: 'global' });

  const externalServerValidation = (): boolean => true;

  const createCommonRules = (): CreateCommonRules => ({
    createExternalValidationRule: () => ({
      externalServerValidation,
    }),
    createRequiredAmountRule: () => ({
      required: helpers.withMessage(t('transactions.events.form.amount.validation.non_empty'), required),
    }),
    createRequiredAssetRule: () => ({
      required: helpers.withMessage(t('transactions.events.form.asset.validation.non_empty'), required),
    }),
    createRequiredAtLeastOne: () => ({
      minLength: minLength(1),
      required,
    }),
    createRequiredBlockNumberRule: () => ({
      required: helpers.withMessage(t('transactions.events.form.block_number.validation.non_empty'), required),
    }),
    createRequiredEventIdentifierRule: (condition?: () => boolean) => ({
      required: helpers.withMessage(
        t('transactions.events.form.event_identifier.validation.non_empty'),
        condition === undefined ? required : requiredIf(condition),
      ),
    }),
    createRequiredEventSubtypeRule: () => ({
      required: helpers.withMessage(t('transactions.events.form.event_subtype.validation.non_empty'), required),
    }),
    createRequiredEventTypeRule: () => ({
      required: helpers.withMessage(t('transactions.events.form.event_type.validation.non_empty'), required),
    }),
    createRequiredFeeAssetRule: (requiredCondition: ValidationRuleWithoutParams = required) => ({
      required: helpers.withMessage(
        t('transactions.events.form.fee_asset.validation.non_empty'),
        requiredCondition,
      ),
    }),
    createRequiredFeeRule: (requiredCondition: ValidationRuleWithoutParams = required) => ({
      required: helpers.withMessage(
        t('transactions.events.form.fee.validation.non_empty'),
        requiredCondition,
      ),
    }),
    createRequiredLocationRule: () => ({
      required: helpers.withMessage(t('transactions.events.form.location.validation.non_empty'), required),
    }),
    createRequiredSequenceIndexRule: () => ({
      required: helpers.withMessage(t('transactions.events.form.sequence_index.validation.non_empty'), required),
    }),
    createRequiredValidatorIndexRule: () => ({
      required: helpers.withMessage(t('transactions.events.form.validator_index.validation.non_empty'), required),
    }),
    createRequiredValidDepositorRule: () => ({
      isValid: helpers.withMessage(
        t('transactions.events.form.depositor.validation.valid'),
        (value: string) => isValidEthAddress(value),
      ),
      required: helpers.withMessage(t('transactions.events.form.depositor.validation.non_empty'), required),
    }),
    createRequiredValidFeeRecipientRule: () => ({
      isValid: helpers.withMessage(
        t('transactions.events.form.fee_recipient.validation.valid'),
        (value: string) => isValidEthAddress(value),
      ),
      required: helpers.withMessage(t('transactions.events.form.fee_recipient.validation.non_empty'), required),
    }),
    createRequiredValidWithdrawalAddressRule: () => ({
      isValid: helpers.withMessage(
        t('transactions.events.form.withdrawal_address.validation.valid'),
        (value: string) => isValidEthAddress(value),
      ),
      required: helpers.withMessage(t('transactions.events.form.withdrawal_address.validation.non_empty'), required),
    }),
    createValidCounterpartyRule: (counterparties: Ref<string[]>) => ({
      isValid: helpers.withMessage(
        t('transactions.events.form.counterparty.validation.valid'),
        (value: string) => !value || get(counterparties).includes(value) || isValidEthAddress(value),
      ),
    }),
    createValidEthAddressRule: () => ({
      isValid: helpers.withMessage(
        t('transactions.events.form.address.validation.valid'),
        (value: string) => !value || isValidEthAddress(value),
      ),
    }),
    createValidProductRule: (products: Ref<string[]>) => ({
      isValid: helpers.withMessage(
        t('transactions.events.form.product.validation.valid'),
        (value: string) => !value || get(products).includes(value),
      ),
    }),
    createValidSolanaAddressRule: () => ({
      isValid: helpers.withMessage(
        t('transactions.events.form.address.validation.valid'),
        (value: string) => !value || isValidSolanaAddress(value),
      ),
    }),
    createValidSolanaSignatureRule: () => ({
      isValid: helpers.withMessage(
        t('transactions.events.form.signature.validation.valid'),
        (value: string) => isValidSolanaSignature(value),
      ),
      required: helpers.withMessage(t('transactions.events.form.signature.validation.non_empty'), required),
    }),
    createValidTxHashRule: () => ({
      isValid: helpers.withMessage(
        t('transactions.events.form.tx_hash.validation.valid'),
        (value: string) => isValidEvmTxHash(value),
      ),
      required: helpers.withMessage(t('transactions.events.form.tx_hash.validation.non_empty'), required),
    }),
  });

  return {
    createCommonRules,
  };
}
