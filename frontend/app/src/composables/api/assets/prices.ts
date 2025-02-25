import { snakeCaseTransformer } from '@/services/axios-transformers';
import { handleResponse, validStatus, validWithoutSessionStatus } from '@/services/utils';
import { api } from '@/services/rotkehlchen-api';
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
import { nonEmptyProperties } from '@/utils/data';
import type { ActionResult } from '@rotki/common';

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
    const response = await api.instance.get<ActionResult<HistoricalPrice[]>>('/assets/prices/historical', {
      params: payload
        ? snakeCaseTransformer(nonEmptyProperties(payload, {
          removeEmptyString: true,
        }))
        : null,
      validateStatus: validWithoutSessionStatus,
    });

    return HistoricalPrices.parse(handleResponse(response));
  };

  const addHistoricalPrice = async (price: HistoricalPriceFormPayload): Promise<boolean> => {
    const response = await api.instance.put<ActionResult<boolean>>(
      '/assets/prices/historical',
      snakeCaseTransformer(price),
      {
        validateStatus: validWithoutSessionStatus,
      },
    );

    return handleResponse(response);
  };

  const editHistoricalPrice = async (price: HistoricalPriceFormPayload): Promise<boolean> => {
    const response = await api.instance.patch<ActionResult<boolean>>(
      '/assets/prices/historical',
      snakeCaseTransformer(price),
      {
        validateStatus: validWithoutSessionStatus,
      },
    );

    return handleResponse(response);
  };

  const deleteHistoricalPrice = async (payload: HistoricalPriceDeletePayload): Promise<boolean> => {
    const response = await api.instance.delete<ActionResult<boolean>>('/assets/prices/historical', {
      data: snakeCaseTransformer(payload),
      validateStatus: validWithoutSessionStatus,
    });

    return handleResponse(response);
  };

  const fetchLatestPrices = async (payload?: Partial<ManualPricePayload>): Promise<ManualPrice[]> => {
    const response = await api.instance.post<ActionResult<ManualPrice[]>>(
      '/assets/prices/latest/all',
      payload
        ? snakeCaseTransformer(nonEmptyProperties(payload, {
          removeEmptyString: true,
        }))
        : null,
      {
        validateStatus: validStatus,
      },
    );

    return ManualPrices.parse(handleResponse(response));
  };

  const addLatestPrice = async (payload: ManualPriceFormPayload): Promise<boolean> => {
    const response = await api.instance.put<ActionResult<boolean>>(
      '/assets/prices/latest',
      snakeCaseTransformer(payload),
      {
        validateStatus: validStatus,
      },
    );

    return handleResponse(response);
  };

  const deleteLatestPrice = async (asset: string): Promise<boolean> => {
    const response = await api.instance.delete<ActionResult<boolean>>('/assets/prices/latest', {
      data: {
        asset,
      },
      validateStatus: validStatus,
    });

    return handleResponse(response);
  };

  const fetchNftsPrices = async (): Promise<NftPriceArray> => {
    const response = await api.instance.post<ActionResult<NftPriceArray>>('/nfts/prices', null, {
      validateStatus: validStatus,
    });

    return NftPriceArray.parse(handleResponse(response));
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
