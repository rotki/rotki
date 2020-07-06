import { ApiManualBalances, SupportedAssets } from '@/services/types-api';
import { ManualBalance, SupportedAsset } from '@/services/types-model';
import { bigNumberify } from '@/utils/bignumbers';

export function convertManualBalances(
  manualBalances: ApiManualBalances
): ManualBalance[] {
  return manualBalances.balances.map(value => ({
    amount: bigNumberify(value.amount),
    asset: value.asset,
    label: value.label,
    location: value.location,
    tags: value.tags,
    usdValue: bigNumberify(value.usd_value)
  }));
}

export function convertSupportedAssets(
  supportedAssets: SupportedAssets
): SupportedAsset[] {
  return Object.keys(supportedAssets).map(key => ({
    key,
    ...supportedAssets[key]
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
