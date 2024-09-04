import { fetchExternalAsync } from '@/services/utils';
import { api } from '@/services/rotkehlchen-api';
import { ProtocolVersion } from '@/types/defi';
import type { PendingTask } from '@/types/task';

interface UseYearnApiReturn { fetchYearnVaultsBalances: (protocolVersion?: ProtocolVersion) => Promise<PendingTask> }

export function useYearnApi(): UseYearnApiReturn {
  const fetchYearnVaultsBalances = (protocolVersion: ProtocolVersion = ProtocolVersion.V1): Promise<PendingTask> => {
    const path = protocolVersion === ProtocolVersion.V1 ? 'vaults' : 'vaultsv2';
    const url = `/blockchains/eth/modules/yearn/${path}/balances`;
    return fetchExternalAsync(api.instance, url);
  };

  return {
    fetchYearnVaultsBalances,
  };
}
