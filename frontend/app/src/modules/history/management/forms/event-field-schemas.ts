import { isValidBtcTxHash, isValidEthAddress, isValidEvmTxHash, isValidSolanaAddress, isValidSolanaSignature } from '@rotki/common';
import { z } from 'zod';
import { msg } from '@/message-key';

/**
 * The zod counterparts of the shared event-form validation rules.
 *
 * - Messages are i18n **keys**, not resolved strings, so schemas stay free of Vue and i18n and are
 *   testable as plain data; `useForm` resolves them at the Vue boundary. Branded with `msg.$t` so
 *   the unused-key lint rule counts them.
 * - The "valid" check tolerates an empty value, so an empty required field reports only "required".
 *
 * Each is a function, not a constant: zod schemas are mutable builders, so a shared instance would
 * let a `.refine()` in one form leak into another.
 */

export function requiredAmount(): z.ZodString {
  return z.string().min(1, msg.$t('transactions.events.form.amount.validation.non_empty'));
}

export function requiredAsset(): z.ZodString {
  return z.string().min(1, msg.$t('transactions.events.form.asset.validation.non_empty'));
}

export function requiredLocation(): z.ZodString {
  return z.string().min(1, msg.$t('transactions.events.form.location.validation.non_empty'));
}

export function requiredSequenceIndex(): z.ZodString {
  return z.string().min(1, msg.$t('transactions.events.form.sequence_index.validation.non_empty'));
}

export function requiredBlockNumber(): z.ZodString {
  return z.string().min(1, msg.$t('transactions.events.form.block_number.validation.non_empty'));
}

export function requiredValidatorIndex(): z.ZodString {
  return z.string().min(1, msg.$t('transactions.events.form.validator_index.validation.non_empty'));
}

export function requiredEventType(): z.ZodString {
  return z.string().min(1, msg.$t('transactions.events.form.event_type.validation.non_empty'));
}

export function requiredEventSubtype(): z.ZodString {
  return z.string().min(1, msg.$t('transactions.events.form.event_subtype.validation.non_empty'));
}

/**
 * The three required-and-valid EVM address fields. They are separate functions rather than one
 * parameterised by its messages because the unused-key lint only counts literal `msg.$t` arguments.
 */
export function requiredFeeRecipient(): z.ZodType<string> {
  return z
    .string()
    .min(1, msg.$t('transactions.events.form.fee_recipient.validation.non_empty'))
    .refine(
      value => !value || isValidEthAddress(value),
      msg.$t('transactions.events.form.fee_recipient.validation.valid'),
    );
}

export function requiredWithdrawalAddress(): z.ZodType<string> {
  return z
    .string()
    .min(1, msg.$t('transactions.events.form.withdrawal_address.validation.non_empty'))
    .refine(
      value => !value || isValidEthAddress(value),
      msg.$t('transactions.events.form.withdrawal_address.validation.valid'),
    );
}

export function requiredDepositor(): z.ZodType<string> {
  return z
    .string()
    .min(1, msg.$t('transactions.events.form.depositor.validation.non_empty'))
    .refine(
      value => !value || isValidEthAddress(value),
      msg.$t('transactions.events.form.depositor.validation.valid'),
    );
}

/** An optional EVM address: blank is allowed, anything present must be a valid address. */
export function optionalEthAddress(): z.ZodType<string> {
  return z.string().refine(
    value => !value || isValidEthAddress(value),
    msg.$t('transactions.events.form.address.validation.valid'),
  );
}

/** An optional Solana address, same shape as {@link optionalEthAddress}. */
export function optionalSolanaAddress(): z.ZodType<string> {
  return z.string().refine(
    value => !value || isValidSolanaAddress(value),
    msg.$t('transactions.events.form.address.validation.valid'),
  );
}

export function requiredEvmTxHash(): z.ZodType<string> {
  return z
    .string()
    .min(1, msg.$t('transactions.events.form.tx_hash.validation.non_empty'))
    .refine(
      value => !value || isValidEvmTxHash(value),
      msg.$t('transactions.events.form.tx_hash.validation.valid'),
    );
}

export function requiredSolanaSignature(): z.ZodType<string> {
  return z
    .string()
    .min(1, msg.$t('transactions.events.form.signature.validation.non_empty'))
    .refine(
      value => !value || isValidSolanaSignature(value),
      msg.$t('transactions.events.form.signature.validation.valid'),
    );
}

export function requiredBitcoinTxId(): z.ZodType<string> {
  return z
    .string()
    .min(1, msg.$t('transactions.events.form.tx_id.validation.non_empty'))
    .refine(
      value => !value || isValidBtcTxHash(value),
      msg.$t('transactions.events.form.tx_id.validation.valid'),
    );
}

/**
 * A counterparty is valid when it is blank, one of the known counterparties, or an EVM address.
 * The known list is passed in because it is loaded at runtime.
 */
export function validCounterparty(counterparties: () => string[]): z.ZodType<string> {
  return z.string().refine(
    value => !value || counterparties().includes(value) || isValidEthAddress(value),
    msg.$t('transactions.events.form.counterparty.validation.valid'),
  );
}

/**
 * A field with no client-side constraint, kept as a named schema because these fields still receive
 * server* errors. It replaces the Vuelidate `externalServerValidation` no-op rule, whose only job
 * was to give `$externalResults` somewhere to attach.
 */
export function serverValidatedOnly(): z.ZodString {
  return z.string();
}

/**
 * A value the form carries but never validates, named so that the absence of a rule reads as a
 * decision rather than an omission.
 *
 * `priceIntent` is a pending historic-price write that `HistoryEventAssetPriceForm` reports upwards
 * for the form to run at save time. It is bound to no input of its own, so a structural rule over it
 * could only fail with nothing on screen to explain why, the same error-sink the no-op Vuelidate
 * rules were. Its shape is enforced by `PriceIntent` at the type level instead.
 */
export function carriedThrough(): z.ZodOptional<z.ZodUnknown> {
  return z.unknown().optional();
}
