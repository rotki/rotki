import { SupportedAsset } from '@/services/assets/types';
import { SupportedAssets } from '@/services/types-api';

export function convertSupportedAssets(
  supportedAssets: SupportedAssets
): SupportedAsset[] {
  return Object.keys(supportedAssets).map(identifier => ({
    identifier,
    ...supportedAssets[identifier]
  }));
}

export function deserializeApiErrorMessage(
  message: string
): { [key: string]: string[] } | undefined {
  try {
    return JSON.parse(message);
  } catch (e) {
    return undefined;
  }
}
