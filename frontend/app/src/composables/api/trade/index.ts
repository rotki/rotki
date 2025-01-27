import type { ActionResult } from '@rotki/common';
import { snakeCaseTransformer } from '@/services/axios-transformers';
import { api } from '@/services/rotkehlchen-api';
import { handleResponse, validStatus } from '@/services/utils';
import { z } from 'zod';

interface UseTradeApiReturn {
  prepareERC20Transfer: (payload: PrepareERC20TransferPayload) => Promise<PrepareERC20TransferResponse>;
  prepareNativeTransfer: (payload: PrepareNativeTransferPayload) => Promise<PrepareNativeTransferResponse>;
  getIsInteractedBefore: (fromAddress: string, toAddress: string) => Promise<boolean>;
}

interface PrepareTransferPayload {
  fromAddress: string;
  toAddress: string;
  amount: string;
}

interface PrepareERC20TransferPayload extends PrepareTransferPayload {
  token: string;
}

const PrepareERC20TransferResponse = z.object({
  chainId: z.number(),
  data: z.string(),
  from: z.string(),
  gas: z.number(),
  maxFeePerGas: z.number(),
  maxPriorityFeePerGas: z.number(),
  nonce: z.number(),
  to: z.string(),
  value: z.number().transform(arg => BigInt(arg)),
});

type PrepareERC20TransferResponse = z.infer<typeof PrepareERC20TransferResponse>;

interface PrepareNativeTransferPayload extends PrepareTransferPayload {
  blockchain: string;
}

const PrepareNativeTransferResponse = z.object({
  from: z.string(),
  maxFeePerGas: z.number().transform(arg => arg.toString()),
  maxPriorityFeePerGas: z.number().transform(arg => arg.toString()),
  nonce: z.number(),
  to: z.string(),
  value: z.number().transform(arg => BigInt(arg)),
});

type PrepareNativeTransferResponse = z.infer<typeof PrepareNativeTransferResponse>;

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
