import { SupportedAsset } from '@rotki/common/lib/data';
import { SupportedAssets } from '@/services/types-api';

export function convertSupportedAssets(
  supportedAssets: SupportedAssets
): SupportedAsset[] {
  return Object.keys(supportedAssets).map(identifier => ({
    identifier,
    ...supportedAssets[identifier]
  }));
}
