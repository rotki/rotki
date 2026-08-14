import { isValidEthAddress, isValidHyperliquidTokenAddress, isValidSolanaAddress } from '@rotki/common';
import { z, type ZodType } from 'zod';
import { EVM_TOKEN, HYPERLIQUID_TOKEN, SOLANA_TOKEN } from '@/modules/assets/types';
import { requiredField } from '@/modules/core/form/fields';

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
