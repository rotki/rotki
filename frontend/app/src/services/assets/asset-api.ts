import { AxiosInstance, AxiosTransformer } from 'axios';
import {
  CustomTokenResponse,
  CustomEthereumToken
} from '@/services/assets/types';
import {
  axiosSnakeCaseTransformer,
  setupTransformer
} from '@/services/axios-tranformers';
import { ActionResult } from '@/services/types-api';
import { handleResponse, validStatus, validTaskStatus } from '@/services/utils';

export class AssetApi {
  private readonly axios: AxiosInstance;
  private readonly baseTransformer: AxiosTransformer[];

  constructor(axios: AxiosInstance) {
    this.axios = axios;
    this.baseTransformer = setupTransformer([]);
  }

  customTokens(): Promise<CustomEthereumToken[]> {
    return this.axios
      .get<ActionResult<CustomEthereumToken[]>>('/assets/ethereum', {
        validateStatus: validTaskStatus,
        transformResponse: this.baseTransformer
      })
      .then(handleResponse);
  }

  addCustomToken(token: CustomEthereumToken): Promise<CustomTokenResponse> {
    return this.axios
      .put<ActionResult<CustomTokenResponse>>(
        '/assets/ethereum',
        axiosSnakeCaseTransformer({ token }),
        {
          validateStatus: validStatus,
          transformResponse: this.baseTransformer
        }
      )
      .then(handleResponse);
  }

  editCustomToken(token: CustomEthereumToken): Promise<CustomTokenResponse> {
    return this.axios
      .patch<ActionResult<CustomTokenResponse>>(
        '/assets/ethereum',
        axiosSnakeCaseTransformer({ token }),
        {
          validateStatus: validStatus,
          transformResponse: this.baseTransformer
        }
      )
      .then(handleResponse);
  }

  deleteCustomToken(address: string): Promise<boolean> {
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
}
