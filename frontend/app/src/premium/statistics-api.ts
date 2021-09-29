import { StatisticsApi } from '@rotki/common/lib/premium';
import {
  LocationData,
  OwnedAssets,
  TimedAssetBalances,
  TimedBalances
} from '@rotki/common/lib/statistics';
import { axiosCamelCaseTransformer } from '@/services/axios-tranformers';
import { api } from '@/services/rotkehlchen-api';

export const statisticsApi: StatisticsApi = {
  async assetValueDistribution(): Promise<TimedAssetBalances> {
    const data = await api.queryLatestAssetValueDistribution();
    return TimedAssetBalances.parse(axiosCamelCaseTransformer(data));
  },
  async locationValueDistribution(): Promise<LocationData> {
    const data = await api.queryLatestLocationValueDistribution();
    return LocationData.parse(axiosCamelCaseTransformer(data));
  },
  async ownedAssets(): Promise<OwnedAssets> {
    const ownedAssets = await api.assets.queryOwnedAssets();
    return OwnedAssets.parse(ownedAssets);
  },
  async timedBalances(
    asset: string,
    start: number,
    end: number
  ): Promise<TimedBalances> {
    const balances = await api.queryTimedBalancesData(asset, start, end);
    return TimedBalances.parse(axiosCamelCaseTransformer(balances));
  }
};
