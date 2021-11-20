import { ActionResult, SupportedAsset } from '@rotki/common/lib/data';
import { AxiosInstance, AxiosResponseTransformer } from 'axios';
import {
  AssetIdResponse,
  AssetPriceArray,
  ConflictResolution,
  EthereumToken,
  HistoricalPrice,
  HistoricalPriceDeletePayload,
  HistoricalPricePayload
} from '@/services/assets/types';
import {
  axiosSnakeCaseTransformer,
  setupTransformer
} from '@/services/axios-tranformers';
import { PendingTask, SupportedAssets } from '@/services/types-api';
import {
  handleResponse,
  validStatus,
  validTaskStatus,
  validWithoutSessionStatus,
  validWithSessionAndExternalService
} from '@/services/utils';

export class AssetApi {
  private readonly axios: AxiosInstance;
  private readonly baseTransformer: AxiosResponseTransformer[];

  constructor(axios: AxiosInstance) {
    this.axios = axios;
    this.baseTransformer = setupTransformer([]);
  }

  ethereumTokens(): Promise<EthereumToken[]> {
    return this.axios
      .get<ActionResult<EthereumToken[]>>('/assets/ethereum', {
        validateStatus: validTaskStatus,
        transformResponse: this.baseTransformer
      })
      .then(handleResponse);
  }

  addEthereumToken(
    token: Omit<EthereumToken, 'identifier'>
  ): Promise<AssetIdResponse> {
    return this.axios
      .put<ActionResult<AssetIdResponse>>(
        '/assets/ethereum',
        axiosSnakeCaseTransformer({ token }),
        {
          validateStatus: validStatus,
          transformResponse: this.baseTransformer
        }
      )
      .then(handleResponse);
  }

  editEthereumToken(
    token: Omit<EthereumToken, 'identifier'>
  ): Promise<AssetIdResponse> {
    return this.axios
      .patch<ActionResult<AssetIdResponse>>(
        '/assets/ethereum',
        axiosSnakeCaseTransformer({ token }),
        {
          validateStatus: validStatus,
          transformResponse: this.baseTransformer
        }
      )
      .then(handleResponse);
  }

  deleteEthereumToken(address: string): Promise<boolean> {
    return this.axios
      .delete<ActionResult<boolean>>('/assets/ethereum', {
        data: axiosSnakeCaseTransformer({ address }),
        validateStatus: validStatus
      })
      .then(handleResponse);
  }

  uploadIcon(identifier: string, file: File): Promise<boolean> {
    const data = new FormData();
    data.append('file', file);
    return this.axios
      .post<ActionResult<boolean>>(`/assets/${identifier}/icon`, data, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      })
      .then(handleResponse);
  }

  setIcon(identifier: string, file: string): Promise<boolean> {
    return this.axios
      .put<ActionResult<boolean>>(`/assets/${identifier}/icon`, {
        file
      })
      .then(handleResponse);
  }

  assetTypes(): Promise<string[]> {
    return this.axios
      .get<ActionResult<string[]>>('/assets/types', {
        validateStatus: validWithoutSessionStatus
      })
      .then(handleResponse);
  }

  ignoredAssets(): Promise<string[]> {
    return this.axios
      .get<ActionResult<string[]>>('/assets/ignored', {
        validateStatus: validStatus
      })
      .then(handleResponse);
  }

  modifyAsset(add: boolean, asset: string): Promise<string[]> {
    if (add) {
      return this.addIgnoredAsset(asset);
    }
    return this.removeIgnoredAsset(asset);
  }

  addIgnoredAsset(asset: string): Promise<string[]> {
    return this.axios
      .put<ActionResult<string[]>>(
        '/assets/ignored',
        {
          assets: [asset]
        },
        {
          validateStatus: validStatus
        }
      )
      .then(handleResponse);
  }

  removeIgnoredAsset(asset: string): Promise<string[]> {
    return this.axios
      .delete<ActionResult<string[]>>('/assets/ignored', {
        data: {
          assets: [asset]
        },
        validateStatus: validStatus
      })
      .then(handleResponse);
  }

  async allAssets(): Promise<SupportedAssets> {
    return this.axios
      .get<ActionResult<SupportedAssets>>('/assets/all', {
        validateStatus: validWithSessionAndExternalService,
        transformResponse: setupTransformer([], true)
      })
      .then(handleResponse);
  }

  queryOwnedAssets(): Promise<string[]> {
    return this.axios
      .get<ActionResult<string[]>>('/assets', {
        validateStatus: validStatus
      })
      .then(handleResponse);
  }

  addAsset(
    asset: Omit<SupportedAsset, 'identifier'>
  ): Promise<AssetIdResponse> {
    return this.axios
      .put<ActionResult<AssetIdResponse>>(
        '/assets/all',
        axiosSnakeCaseTransformer(asset),
        {
          validateStatus: validStatus,
          transformResponse: this.baseTransformer
        }
      )
      .then(handleResponse);
  }

  editAsset(asset: SupportedAsset): Promise<boolean> {
    return this.axios
      .patch<ActionResult<boolean>>(
        '/assets/all',
        axiosSnakeCaseTransformer(asset),
        {
          validateStatus: validStatus,
          transformResponse: this.baseTransformer
        }
      )
      .then(handleResponse);
  }

  deleteAsset(identifier: string): Promise<boolean> {
    return this.axios
      .delete<ActionResult<boolean>>('/assets/all', {
        data: axiosSnakeCaseTransformer({ identifier }),
        validateStatus: validStatus
      })
      .then(handleResponse);
  }

  checkForAssetUpdate(): Promise<PendingTask> {
    return this.axios
      .get<ActionResult<PendingTask>>('/assets/updates', {
        params: axiosSnakeCaseTransformer({ asyncQuery: true }),
        validateStatus: validWithoutSessionStatus,
        transformResponse: this.baseTransformer
      })
      .then(handleResponse);
  }

  performUpdate(
    version: number,
    conflicts?: ConflictResolution
  ): Promise<PendingTask> {
    const data = {
      async_query: true,
      up_to_version: version,
      conflicts
    };

    return this.axios
      .post<ActionResult<PendingTask>>('/assets/updates', data, {
        validateStatus: validStatus,
        transformResponse: this.baseTransformer
      })
      .then(handleResponse);
  }

  mergeAssets(sourceIdentifier: string, targetAsset: string): Promise<boolean> {
    const data = axiosSnakeCaseTransformer({
      sourceIdentifier,
      targetAsset
    });
    return this.axios
      .put<ActionResult<boolean>>('/assets/replace', data, {
        validateStatus: validStatus,
        transformResponse: this.baseTransformer
      })
      .then(handleResponse);
  }

  historicalPrices(
    payload?: Partial<HistoricalPricePayload>
  ): Promise<HistoricalPrice[]> {
    return this.axios
      .get<ActionResult<HistoricalPrice[]>>('/assets/prices/historical', {
        params: axiosSnakeCaseTransformer(payload),
        validateStatus: validWithoutSessionStatus,
        transformResponse: setupTransformer(['price'])
      })
      .then(handleResponse);
  }

  async addHistoricalPrice(price: HistoricalPrice): Promise<boolean> {
    return this.axios
      .put<ActionResult<boolean>>(
        '/assets/prices/historical',
        axiosSnakeCaseTransformer(price),
        {
          validateStatus: validWithoutSessionStatus
        }
      )
      .then(handleResponse);
  }

  async editHistoricalPrice(price: HistoricalPrice): Promise<boolean> {
    return this.axios
      .patch<ActionResult<boolean>>(
        '/assets/prices/historical',
        axiosSnakeCaseTransformer(price),
        {
          validateStatus: validWithoutSessionStatus
        }
      )
      .then(handleResponse);
  }

  async deleteHistoricalPrice(
    payload: HistoricalPriceDeletePayload
  ): Promise<boolean> {
    return this.axios
      .delete<ActionResult<boolean>>('/assets/prices/historical', {
        data: axiosSnakeCaseTransformer(payload),
        validateStatus: validWithoutSessionStatus
      })
      .then(handleResponse);
  }

  restoreAssetsDatabase(
    reset: String,
    ignoreWarnings: boolean
  ): Promise<boolean> {
    return this.axios
      .delete<ActionResult<boolean>>('/assets/updates', {
        data: axiosSnakeCaseTransformer({ reset, ignoreWarnings }),
        validateStatus: validStatus,
        transformResponse: this.baseTransformer
      })
      .then(handleResponse);
  }

  fetchCurrentPrices(): Promise<AssetPriceArray> {
    return this.axios
      .get<ActionResult<AssetPriceArray>>('/assets/prices/current', {
        validateStatus: validStatus,
        transformResponse: this.baseTransformer
      })
      .then(handleResponse);
  }

  deleteCurrentPrice(asset: string): Promise<boolean> {
    return this.axios
      .delete<ActionResult<boolean>>('/assets/prices/current', {
        validateStatus: validStatus,
        data: {
          asset
        },
        transformResponse: this.baseTransformer
      })
      .then(handleResponse);
  }

  setCurrentPrice(
    fromAsset: string,
    toAsset: string,
    price: string
  ): Promise<boolean> {
    return this.axios
      .put<ActionResult<boolean>>(
        '/assets/prices/current',
        axiosSnakeCaseTransformer({
          fromAsset,
          toAsset,
          price
        }),
        {
          validateStatus: validStatus,
          transformResponse: this.baseTransformer
        }
      )
      .then(handleResponse);
  }
}
