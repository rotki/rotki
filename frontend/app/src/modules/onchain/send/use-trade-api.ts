import { type BigNumber, NumericString, Zero } from '@rotki/common';
import { api } from '@/modules/api/rotki-api';
import {
  type GetAssetBalancePayload,
  type PrepareERC20TransferPayload,
  PrepareERC20TransferResponse,
  type PrepareNativeTransferPayload,
  PrepareNativeTransferResponse,
} from '@/modules/onchain/types';

interface UseTradeApiReturn {
  prepareERC20Transfer: (payload: PrepareERC20TransferPayload) => Promise<PrepareERC20TransferResponse>;
  prepareNativeTransfer: (payload: PrepareNativeTransferPayload) => Promise<PrepareNativeTransferResponse>;
  getIsInteractedBefore: (fromAddress: string, toAddress: string) => Promise<boolean>;
  getAssetBalance: (payload: GetAssetBalancePayload) => Promise<BigNumber>;
}

export function useTradeApi(): UseTradeApiReturn {
  const prepareERC20Transfer = async (payload: PrepareERC20TransferPayload): Promise<PrepareERC20TransferResponse> => {
    const response = await api.post<PrepareERC20TransferResponse>('/wallet/transfer/token', payload);
    return PrepareERC20TransferResponse.parse(response);
  };

  const prepareNativeTransfer = async (payload: PrepareNativeTransferPayload): Promise<PrepareNativeTransferResponse> => {
    const response = await api.post<PrepareNativeTransferResponse>('/wallet/transfer/native', payload);
    return PrepareNativeTransferResponse.parse(response);
  };

  const getIsInteractedBefore = async (fromAddress: string, toAddress: string): Promise<boolean> => api.post<boolean>('/wallet/interacted', {
    fromAddress,
    toAddress,
  });

  const getAssetBalance = async (payload: GetAssetBalancePayload): Promise<BigNumber> => {
    try {
      const response = await api.post<string>('/wallet/balance', payload);
      return NumericString.parse(response);
    }
    catch {
      return Zero;
    }
  };

  return {
    getAssetBalance,
    getIsInteractedBefore,
    prepareERC20Transfer,
    prepareNativeTransfer,
  };
}
