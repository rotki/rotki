import { fetchExternalAsync } from '@/services/utils';
import { api } from '@/services/rotkehlchen-api';
import type { PendingTask } from '@/types/task';

interface UseMakerDaoApiReturn {
  fetchDsrBalances: () => Promise<PendingTask>;
  fetchDsrHistories: () => Promise<PendingTask>;
  fetchMakerDAOVaults: () => Promise<PendingTask>;
  fetchMakerDAOVaultDetails: () => Promise<PendingTask>;
}

export function useMakerDaoApi(): UseMakerDaoApiReturn {
  const fetchDsrBalances = (): Promise<PendingTask> => {
    const url = 'blockchains/eth/modules/makerdao/dsrbalance';
    return fetchExternalAsync(api.instance, url);
  };

  const fetchDsrHistories = (): Promise<PendingTask> => {
    const url = 'blockchains/eth/modules/makerdao/dsrhistory';
    return fetchExternalAsync(api.instance, url);
  };

  const fetchMakerDAOVaults = (): Promise<PendingTask> => {
    const url = 'blockchains/eth/modules/makerdao/vaults';
    return fetchExternalAsync(api.instance, url);
  };

  const fetchMakerDAOVaultDetails = (): Promise<PendingTask> => {
    const url = '/blockchains/eth/modules/makerdao/vaultdetails';
    return fetchExternalAsync(api.instance, url);
  };

  return {
    fetchDsrBalances,
    fetchDsrHistories,
    fetchMakerDAOVaults,
    fetchMakerDAOVaultDetails,
  };
}
