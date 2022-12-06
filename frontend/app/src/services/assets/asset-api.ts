import { ActionResult, SupportedAsset } from '@rotki/common/lib/data';
import { OwnedAssets } from '@rotki/common/lib/statistics';
import { AxiosInstance } from 'axios';
import {
  AssetIdResponse,
  ConflictResolution,
  HistoricalPrice,
  HistoricalPriceDeletePayload,
  HistoricalPriceFormPayload,
  ManualPricePayload,
  HistoricalPrices,
  ManualPriceFormPayload,
  ManualPrice,
  ManualPrices,
  AssetPriceArray
} from '@/services/assets/types';
import { axiosSnakeCaseTransformer } from '@/services/axios-tranformers';
import { PendingTask } from '@/services/types-api';
import {
  handleResponse,
  validFileOperationStatus,
  validStatus,
  validWithoutSessionStatus
} from '@/services/utils';
import { ActionStatus } from '@/store/types';
import { CustomAsset } from '@/types/assets';
import { assert } from '@/utils/assertions';

export class AssetApi {
  private readonly axios: AxiosInstance;

  constructor(axios: AxiosInstance) {
    this.axios = axios;
  }

  addEthereumToken(
    token: Omit<SupportedAsset, 'identifier'>
  ): Promise<AssetIdResponse> {
    return this.axios
      .put<ActionResult<AssetIdResponse>>(
        '/assets/ethereum',
        axiosSnakeCaseTransformer({ token }),
        {
          validateStatus: validStatus
        }
      )
      .then(handleResponse);
  }

  editEthereumToken(
    token: Omit<SupportedAsset, 'identifier'>
  ): Promise<AssetIdResponse> {
    return this.axios
      .patch<ActionResult<AssetIdResponse>>(
        '/assets/ethereum',
        axiosSnakeCaseTransformer({ token }),
        {
          validateStatus: validStatus
        }
      )
      .then(handleResponse);
  }

  deleteEthereumToken(address: string, chain: string): Promise<boolean> {
    return this.axios
      .delete<ActionResult<boolean>>('/assets/ethereum', {
        data: axiosSnakeCaseTransformer({ address, chain }),
        validateStatus: validStatus
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

  async queryOwnedAssets(): Promise<string[]> {
    const ownedAssets = await this.axios.get<ActionResult<string[]>>(
      '/assets',
      {
        validateStatus: validStatus
      }
    );

    return OwnedAssets.parse(handleResponse(ownedAssets));
  }

  addAsset(
    asset: Omit<SupportedAsset, 'identifier'>
  ): Promise<AssetIdResponse> {
    return this.axios
      .put<ActionResult<AssetIdResponse>>(
        '/assets/all',
        axiosSnakeCaseTransformer(asset),
        {
          validateStatus: validStatus
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
          validateStatus: validStatus
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
        validateStatus: validWithoutSessionStatus
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
        validateStatus: validStatus
      })
      .then(handleResponse);
  }

  async mergeAssets(
    sourceIdentifier: string,
    targetAsset: string
  ): Promise<true> {
    const data = axiosSnakeCaseTransformer({
      sourceIdentifier,
      targetAsset
    });
    const response = await this.axios.put<ActionResult<true>>(
      '/assets/replace',
      data,
      {
        validateStatus: validStatus
      }
    );
    return handleResponse(response);
  }

  async historicalPrices(
    payload?: Partial<ManualPricePayload>
  ): Promise<HistoricalPrice[]> {
    const response = await this.axios.get<ActionResult<HistoricalPrice[]>>(
      '/assets/prices/historical',
      {
        params: axiosSnakeCaseTransformer(payload),
        validateStatus: validWithoutSessionStatus
      }
    );

    return HistoricalPrices.parse(handleResponse(response));
  }

  async addHistoricalPrice(
    price: HistoricalPriceFormPayload
  ): Promise<boolean> {
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

  async editHistoricalPrice(
    price: HistoricalPriceFormPayload
  ): Promise<boolean> {
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
    reset: 'hard' | 'soft',
    ignoreWarnings: boolean
  ): Promise<boolean> {
    return this.axios
      .delete<ActionResult<boolean>>('/assets/updates', {
        data: axiosSnakeCaseTransformer({ reset, ignoreWarnings }),
        validateStatus: validStatus
      })
      .then(handleResponse);
  }

  async fetchNftsPrices(): Promise<AssetPriceArray> {
    const response = await this.axios.post<ActionResult<AssetPriceArray>>(
      '/nfts/prices',
      null,
      {
        validateStatus: validStatus
      }
    );

    return AssetPriceArray.parse(handleResponse(response));
  }

  async fetchLatestPrices(
    payload?: Partial<ManualPricePayload>
  ): Promise<ManualPrice[]> {
    const response = await this.axios.post<ActionResult<ManualPrice[]>>(
      '/assets/prices/latest/all',
      payload,
      {
        validateStatus: validStatus
      }
    );

    return ManualPrices.parse(handleResponse(response));
  }

  addLatestPrice(payload: ManualPriceFormPayload): Promise<boolean> {
    return this.axios
      .put<ActionResult<boolean>>(
        '/assets/prices/latest',
        axiosSnakeCaseTransformer(payload),
        {
          validateStatus: validStatus
        }
      )
      .then(handleResponse);
  }

  deleteLatestPrice(asset: string): Promise<boolean> {
    return this.axios
      .delete<ActionResult<boolean>>('/assets/prices/latest', {
        validateStatus: validStatus,
        data: {
          asset
        }
      })
      .then(handleResponse);
  }

  async importCustom(
    file: File,
    upload = false
  ): Promise<ActionResult<boolean>> {
    if (upload) {
      const data = new FormData();
      data.append('file', file);
      const response = await this.axios.post('/assets/user', data, {
        validateStatus: validFileOperationStatus,
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      return handleResponse(response);
    }

    const response = await this.axios.put(
      '/assets/user',
      { action: 'upload', file: file.path },
      {
        validateStatus: validFileOperationStatus
      }
    );
    return handleResponse(response);
  }

  async exportCustom(directory?: string): Promise<ActionStatus> {
    try {
      if (!directory) {
        const response = await this.axios.put(
          '/assets/user',
          { action: 'download' },
          {
            responseType: 'blob',
            validateStatus: validFileOperationStatus
          }
        );
        if (response.status === 200) {
          const url = window.URL.createObjectURL(response.data);
          const link = document.createElement('a');
          link.id = 'custom-assets-link';
          link.href = url;
          link.setAttribute('download', 'assets.zip');
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
          return { success: true };
        }
        const body = await (response.data as Blob).text();
        const result: ActionResult<null> = JSON.parse(body);

        return { success: false, message: result.message };
      }
      const response = await this.axios.put<ActionResult<{ file: string }>>(
        '/assets/user',
        { action: 'download', destination: directory },
        {
          validateStatus: validFileOperationStatus
        }
      );
      const data = handleResponse(response);
      assert(data.file);
      return {
        success: true
      };
    } catch (e: any) {
      return { success: false, message: e.message };
    }
  }

  async getCustomAssetTypes(): Promise<string[]> {
    return this.axios
      .get<ActionResult<string[]>>('/assets/custom/types', {
        validateStatus: validStatus
      })
      .then(handleResponse);
  }

  async addCustomAsset(
    asset: Omit<CustomAsset, 'identifier'>
  ): Promise<string> {
    return this.axios
      .put<ActionResult<string>>(
        '/assets/custom',
        axiosSnakeCaseTransformer(asset),
        {
          validateStatus: validStatus
        }
      )
      .then(handleResponse);
  }

  async editCustomAsset(asset: CustomAsset): Promise<boolean> {
    return this.axios
      .patch<ActionResult<boolean>>(
        '/assets/custom',
        axiosSnakeCaseTransformer(asset),
        {
          validateStatus: validStatus
        }
      )
      .then(handleResponse);
  }

  async deleteCustomAsset(identifier: string): Promise<boolean> {
    return this.axios
      .delete<ActionResult<boolean>>('/assets/custom', {
        data: axiosSnakeCaseTransformer({ identifier }),
        validateStatus: validStatus
      })
      .then(handleResponse);
  }
}
