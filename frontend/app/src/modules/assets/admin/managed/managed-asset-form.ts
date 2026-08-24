import { isValidEthAddress, isValidHyperliquidTokenAddress, isValidSolanaAddress, type SupportedAsset } from '@rotki/common';
import { z, type ZodType } from 'zod';
import { EVM_TOKEN, HYPERLIQUID_TOKEN, SOLANA_TOKEN } from '@/modules/assets/types';
import { requiredField } from '@/modules/core/form/fields';

/**
 * The fields the payload admits as null and an input has to hold as a string.
 *
 * Not every nullable field is one of these: `decimals` and `started` are nullable too, and are
 * bound through their own converters, which have a use for the difference between empty and zero.
 */
type OptionalTextField =
  | 'address'
  | 'coingecko'
  | 'collectibleId'
  | 'cryptocompare'
  | 'forked'
  | 'name'
  | 'protocol'
  | 'swappedFor'
  | 'symbol';

/**
 * The asset as the form's inputs hold it: the optional text fields are always a string, empty where
 * the payload has nothing.
 *
 * Derived from the payload rather than spelled out, so a field added to `SupportedAsset` reaches
 * the form without anyone having to add it here too.
 */
export type ManagedAssetFormState =
  Omit<SupportedAsset, OptionalTextField> & Record<OptionalTextField, string>;

/**
 * Widens the payload into what the inputs can bind to.
 *
 * The empty string survives as far as `buildManagedAssetPayload`, which is where it turns back into
 * an absent field. That is deliberate: the api reads an absent field as "leave it alone" and an
 * empty one as "clear it", and only the payload builder knows which of the two each field wants.
 */
export function toManagedAssetFormState(asset: SupportedAsset): ManagedAssetFormState {
  return {
    ...asset,
    address: asset.address ?? '',
    coingecko: asset.coingecko ?? '',
    collectibleId: asset.collectibleId ?? '',
    cryptocompare: asset.cryptocompare ?? '',
    forked: asset.forked ?? '',
    name: asset.name ?? '',
    protocol: asset.protocol ?? '',
    swappedFor: asset.swappedFor ?? '',
    symbol: asset.symbol ?? '',
  };
}

export interface ManagedAssetMessages {
  addressInvalid: string;
  addressMissing: string;
  assetTypeMissing: string;
  collectibleIdMissing: string;
}

export interface ManagedAssetRules {
  /** The three token types identified by an on-chain address. */
  requiresAddress: boolean;
  /** A collectible, which is the only kind that carries an id. */
  isNft: boolean;
}

/**
 * Each token type spells its address differently, and only its own check applies.
 *
 * A type that is not one of the three has no address format to be wrong about, so nothing is
 * claimed about it: the missing type is the thing to report.
 */
function isAddressOfType(assetType: string | null | undefined, address: string): boolean {
  if (assetType === EVM_TOKEN)
    return isValidEthAddress(address);

  if (assetType === HYPERLIQUID_TOKEN)
    return isValidHyperliquidTokenAddress(address);

  if (assetType === SOLANA_TOKEN)
    return isValidSolanaAddress(address);

  return true;
}

/**
 * The three rules this form has ever had: an asset type, an address for the token types that have
 * one, and an id for a collectible.
 *
 * Everything else passes through. Ten of the fields carried a rule that always returned true, which
 * is where server errors land rather than a rule, and none of them is required. Turning any of them
 * into a structural rule would block the save with nothing on screen to explain it.
 */
export function managedAssetSchema(messages: ManagedAssetMessages, rules: ManagedAssetRules): ZodType {
  const address = rules.requiresAddress
    ? requiredField(messages.addressMissing)
    : z.string().nullish();

  return z.object({
    address,
    assetType: requiredField(messages.assetTypeMissing),
    collectibleId: rules.isNft ? requiredField(messages.collectibleIdMissing) : z.string().nullish(),
  }).passthrough().superRefine((value, ctx) => {
    if (!rules.requiresAddress)
      return;

    // Checked here rather than on the field so it can read the asset type beside it. An empty
    // address is already reported as missing, and saying it is also malformed adds nothing.
    const typed = value.address;
    if (typeof typed !== 'string' || typed.trim() === '')
      return;

    if (!isAddressOfType(value.assetType, typed))
      ctx.addIssue({ code: 'custom', message: messages.addressInvalid, path: ['address'] });
  });
}
