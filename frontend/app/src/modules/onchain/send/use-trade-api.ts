import type { ActionResult } from '@rotki/common';
import {
  type PrepareERC20TransferPayload,
  PrepareERC20TransferResponse,
  type PrepareNativeTransferPayload,
  PrepareNativeTransferResponse,
} from '@/modules/onchain/types';
import { snakeCaseTransformer } from '@/services/axios-transformers';
import { api } from '@/services/rotkehlchen-api';
import { handleResponse, validStatus } from '@/services/utils';

interface UseTradeApiReturn {
  prepareERC20Transfer: (payload: PrepareERC20TransferPayload) => Promise<PrepareERC20TransferResponse>;
  prepareNativeTransfer: (payload: PrepareNativeTransferPayload) => Promise<PrepareNativeTransferResponse>;
  getIsInteractedBefore: (fromAddress: string, toAddress: string) => Promise<boolean>;
}

export function useTradeApi(): UseTradeApiReturn {
  const prepareERC20Transfer = async (payload: PrepareERC20TransferPayload): Promise<PrepareERC20TransferResponse> => {
    const response = await api.instance.post<ActionResult<PrepareERC20TransferResponse>>(
      `/wallet/transfer/token`,
      snakeCaseTransformer(payload),
      {
        validateStatus: validStatus,
      },
    );
    return PrepareERC20TransferResponse.parse(handleResponse(response));
  };

  const prepareNativeTransfer = async (payload: PrepareNativeTransferPayload): Promise<PrepareNativeTransferResponse> => {
    const response = await api.instance.post<ActionResult<PrepareNativeTransferResponse>>(
      `/wallet/transfer/native`,
      snakeCaseTransformer(payload),
      {
        validateStatus: validStatus,
      },
    );
    return PrepareNativeTransferResponse.parse(handleResponse(response));
  };

  const getIsInteractedBefore = async (fromAddress: string, toAddress: string): Promise<boolean> => {
    const response = await api.instance.post<ActionResult<boolean>>(
      `/wallet/interacted`,
      snakeCaseTransformer({
        fromAddress,
        toAddress,
      }),
      {
        validateStatus: validStatus,
      },
    );
    return response.data.result;
  };

  return {
    getIsInteractedBefore,
    prepareERC20Transfer,
    prepareNativeTransfer,
  };
}
