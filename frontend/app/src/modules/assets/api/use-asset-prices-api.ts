import type { Collection } from '@/modules/core/common/collection';
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
  type OraclePriceEntry,
  OraclePricesCollectionResponse,
  type OraclePricesQuery,
} from '@/modules/assets/prices/price-types';
import { defaultApiUrls } from '@/modules/core/api/api-urls';
import { api } from '@/modules/core/api/rotki-api';
import { VALID_WITHOUT_SESSION_STATUS } from '@/modules/core/api/utils';
import { mapCollectionResponse } from '@/modules/core/common/data/collection-utils';

interface UseAssetPriceApiReturn {
  fetchHistoricalPrices: (payload?: Partial<ManualPricePayload>) => Promise<HistoricalPrice[]>;
  addHistoricalPrice: (price: HistoricalPriceFormPayload) => Promise<boolean>;
  editHistoricalPrice: (price: HistoricalPriceFormPayload) => Promise<boolean>;
  deleteHistoricalPrice: (payload: HistoricalPriceDeletePayload) => Promise<boolean>;
  fetchOraclePrices: (query?: OraclePricesQuery) => Promise<Collection<OraclePriceEntry>>;
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

  const fetchOraclePrices = async (query?: OraclePricesQuery): Promise<Collection<OraclePriceEntry>> => {
    const response = await api.get<OraclePricesCollectionResponse>('/prices/oracle', {
      baseURL: defaultApiUrls.colibriApiUrl,
      filterEmptyProperties: { removeEmptyString: true },
      query,
      retry: true,
    });

    return mapCollectionResponse(OraclePricesCollectionResponse.parse(response));
  };

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
    fetchOraclePrices,
  };
}
