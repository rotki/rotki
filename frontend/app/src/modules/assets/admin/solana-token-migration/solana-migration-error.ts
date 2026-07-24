import { isSolanaTokenIdentifier } from '@rotki/common';

/**
 * Returns the first Solana token identifier found in a backend error message,
 * used to suggest merging into the conflicting asset.
 */
export function extractTargetAssetFromError(errorMessage: string): string | null {
  const words = errorMessage.split(/\s+/);
  for (const word of words) {
    if (isSolanaTokenIdentifier(word))
      return word;
  }
  return null;
}

/**
 * Detects the unique-constraint failure raised when the target asset already exists.
 */
export function isUniqueConstraintError(errorMessage: string): boolean {
  return errorMessage.includes('UNIQUE constraint failed: assets.identifier');
}
