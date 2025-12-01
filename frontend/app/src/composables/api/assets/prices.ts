import { api } from '@/modules/api/rotki-api';
import { VALID_WITHOUT_SESSION_STATUS } from '@/modules/api/utils';
import {
  type HistoricalPrice,
  type HistoricalPriceDeletePayload,
  type HistoricalPriceFormPayload,
  HistoricalPrices,
  type ManualPrice,
  type ManualPriceFormPayload,
  type ManualPricePayload,
  ManualPrices,
  NftPriceArray,
} from '@/types/prices';

interface UseAssetPriceApiReturn {
  fetchHistoricalPrices: (payload?: Partial<ManualPricePayload>) => Promise<HistoricalPrice[]>;
  addHistoricalPrice: (price: HistoricalPriceFormPayload) => Promise<boolean>;
  editHistoricalPrice: (price: HistoricalPriceFormPayload) => Promise<boolean>;
  deleteHistoricalPrice: (payload: HistoricalPriceDeletePayload) => Promise<boolean>;
  fetchLatestPrices: (payload?: Partial<ManualPricePayload>) => Promise<ManualPrice[]>;
  addLatestPrice: (payload: ManualPriceFormPayload) => Promise<boolean>;
  deleteLatestPrice: (asset: string) => Promise<boolean>;
  fetchNftsPrices: () => Promise<NftPriceArray>;
}

export function useAssetPricesApi(): UseAssetPriceApiReturn {
  const fetchHistoricalPrices = async (payload?: Partial<ManualPricePayload>): Promise<HistoricalPrice[]> => {
    const response = await api.get<HistoricalPrice[]>('/assets/prices/historical', {
      filterEmptyProperties: { removeEmptyString: true },
      query: payload,
      validStatuses: VALID_WITHOUT_SESSION_STATUS,
    });

    return HistoricalPrices.parse(response);
  };

  const addHistoricalPrice = async (price: HistoricalPriceFormPayload): Promise<boolean> => api.put<boolean>(
    '/assets/prices/historical',
    price,
    {
      validStatuses: VALID_WITHOUT_SESSION_STATUS,
    },
  );

  const editHistoricalPrice = async (price: HistoricalPriceFormPayload): Promise<boolean> => api.patch<boolean>(
    '/assets/prices/historical',
    price,
    {
      validStatuses: VALID_WITHOUT_SESSION_STATUS,
    },
  );

  const deleteHistoricalPrice = async (payload: HistoricalPriceDeletePayload): Promise<boolean> => api.delete<boolean>('/assets/prices/historical', {
    body: payload,
    validStatuses: VALID_WITHOUT_SESSION_STATUS,
  });

  const fetchLatestPrices = async (payload?: Partial<ManualPricePayload>): Promise<ManualPrice[]> => {
    const response = await api.post<ManualPrice[]>(
      '/assets/prices/latest/all',
      payload ?? null,
      {
        filterEmptyProperties: { removeEmptyString: true },
      },
    );

    return ManualPrices.parse(response);
  };

  const addLatestPrice = async (payload: ManualPriceFormPayload): Promise<boolean> => api.put<boolean>(
    '/assets/prices/latest',
    payload,
  );

  const deleteLatestPrice = async (asset: string): Promise<boolean> => api.delete<boolean>('/assets/prices/latest', {
    body: {
      asset,
    },
  });

  const fetchNftsPrices = async (): Promise<NftPriceArray> => {
    const response = await api.post<NftPriceArray>('/nfts/prices', null);

    return NftPriceArray.parse(response);
  };

  return {
    addHistoricalPrice,
    addLatestPrice,
    deleteHistoricalPrice,
    deleteLatestPrice,
    editHistoricalPrice,
    fetchHistoricalPrices,
    fetchLatestPrices,
    fetchNftsPrices,
  };
}
