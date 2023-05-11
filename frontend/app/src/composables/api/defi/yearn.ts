import { fetchExternalAsync } from '@/services/utils';
import { api } from '@/services/rotkehlchen-api';
import { ProtocolVersion } from '@/types/defi';
import { type PendingTask } from '@/types/task';

export const useYearnApi = () => {
  const fetchYearnVaultsHistory = async (
    protocolVersion: ProtocolVersion = ProtocolVersion.V1,
    reset?: boolean
  ): Promise<PendingTask> => {
    const path = protocolVersion === ProtocolVersion.V1 ? 'vaults' : 'vaultsv2';
    const url = `/blockchains/ETH/modules/yearn/${path}/history`;
    const params = reset ? { resetDbData: true } : undefined;
    return fetchExternalAsync(api.instance, url, params);
  };

  const fetchYearnVaultsBalances = async (
    protocolVersion: ProtocolVersion = ProtocolVersion.V1
  ): Promise<PendingTask> => {
    const path = protocolVersion === ProtocolVersion.V1 ? 'vaults' : 'vaultsv2';
    const url = `/blockchains/ETH/modules/yearn/${path}/balances`;
    return fetchExternalAsync(api.instance, url);
  };

  return {
    fetchYearnVaultsHistory,
    fetchYearnVaultsBalances
  };
};
