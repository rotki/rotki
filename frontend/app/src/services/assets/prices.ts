import { type ActionResult } from '@rotki/common/lib/data';
import {
  AssetPriceArray,
  type HistoricalPrice,
  type HistoricalPriceDeletePayload,
  type HistoricalPriceFormPayload,
  HistoricalPrices,
  type ManualPrice,
  type ManualPriceFormPayload,
  type ManualPricePayload,
  ManualPrices
} from '@/services/assets/types';
import { axiosSnakeCaseTransformer } from '@/services/axios-tranformers';
import {
  handleResponse,
  validStatus,
  validWithoutSessionStatus
} from '@/services/utils';
import { api } from '@/services/rotkehlchen-api';
import { nonEmptyProperties } from '@/utils/data';

export const useAssetPricesApi = () => {
  const fetchHistoricalPrices = async (
    payload?: Partial<ManualPricePayload>
  ): Promise<HistoricalPrice[]> => {
    const response = await api.instance.get<ActionResult<HistoricalPrice[]>>(
      '/assets/prices/historical',
      {
        params: payload
          ? axiosSnakeCaseTransformer(nonEmptyProperties(payload, true))
          : null,
        validateStatus: validWithoutSessionStatus
      }
    );

    return HistoricalPrices.parse(handleResponse(response));
  };

  const addHistoricalPrice = async (
    price: HistoricalPriceFormPayload
  ): Promise<boolean> => {
    const response = await api.instance.put<ActionResult<boolean>>(
      '/assets/prices/historical',
      axiosSnakeCaseTransformer(price),
      {
        validateStatus: validWithoutSessionStatus
      }
    );

    return handleResponse(response);
  };

  const editHistoricalPrice = async (
    price: HistoricalPriceFormPayload
  ): Promise<boolean> => {
    const response = await api.instance.patch<ActionResult<boolean>>(
      '/assets/prices/historical',
      axiosSnakeCaseTransformer(price),
      {
        validateStatus: validWithoutSessionStatus
      }
    );

    return handleResponse(response);
  };

  const deleteHistoricalPrice = async (
    payload: HistoricalPriceDeletePayload
  ): Promise<boolean> => {
    const response = await api.instance.delete<ActionResult<boolean>>(
      '/assets/prices/historical',
      {
        data: axiosSnakeCaseTransformer(payload),
        validateStatus: validWithoutSessionStatus
      }
    );

    return handleResponse(response);
  };

  const fetchLatestPrices = async (
    payload?: Partial<ManualPricePayload>
  ): Promise<ManualPrice[]> => {
    const response = await api.instance.post<ActionResult<ManualPrice[]>>(
      '/assets/prices/latest/all',
      payload,
      {
        validateStatus: validStatus
      }
    );

    return ManualPrices.parse(handleResponse(response));
  };

  const addLatestPrice = async (
    payload: ManualPriceFormPayload
  ): Promise<boolean> => {
    const response = await api.instance.put<ActionResult<boolean>>(
      '/assets/prices/latest',
      axiosSnakeCaseTransformer(payload),
      {
        validateStatus: validStatus
      }
    );

    return handleResponse(response);
  };

  const deleteLatestPrice = async (asset: string): Promise<boolean> => {
    const response = await api.instance.delete<ActionResult<boolean>>(
      '/assets/prices/latest',
      {
        validateStatus: validStatus,
        data: {
          asset
        }
      }
    );

    return handleResponse(response);
  };

  const fetchNftsPrices = async (): Promise<AssetPriceArray> => {
    const response = await api.instance.post<ActionResult<AssetPriceArray>>(
      '/nfts/prices',
      null,
      {
        validateStatus: validStatus
      }
    );

    return AssetPriceArray.parse(handleResponse(response));
  };

  return {
    fetchHistoricalPrices,
    addHistoricalPrice,
    editHistoricalPrice,
    deleteHistoricalPrice,
    fetchLatestPrices,
    addLatestPrice,
    deleteLatestPrice,
    fetchNftsPrices
  };
};
