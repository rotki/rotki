import type {
  PrepareERC20TransferPayload,
  PrepareERC20TransferResponse,
  PrepareNativeTransferPayload,
  PrepareNativeTransferResponse,
  TransactionParams,
} from '@/modules/onchain/types';
import { assert } from '@rotki/common';

interface ValidationOptions {
  params: TransactionParams;
  connectedAddress: string | undefined;
  connectedChainId: number | undefined;
  getEvmChainName: (chain: string) => string | undefined;
}

interface TransactionDependencies {
  prepareERC20Transfer: (payload: PrepareERC20TransferPayload) => Promise<PrepareERC20TransferResponse>;
  prepareNativeTransfer: (payload: PrepareNativeTransferPayload) => Promise<PrepareNativeTransferResponse>;
}

interface ErrorHandlers {
  setPreparing: (value: boolean) => void;
  setWaitingForWalletConfirmation: (value: boolean) => void;
  updateTransactionStatus: (hash: string, status: 'completed' | 'failed') => void;
}

export function validateTransactionRequirements(options: ValidationOptions): {
  chainId: number;
  evmChain: string;
  fromAddress: string;
} {
  const { connectedAddress, connectedChainId, getEvmChainName, params } = options;
  const fromAddress = connectedAddress;
  const chainId = connectedChainId;
  const evmChain = getEvmChainName(params.chain);

  if (!chainId || !evmChain) {
    throw new Error('No chain ID available');
  }

  assert(fromAddress);

  return { chainId, evmChain, fromAddress };
}

export async function prepareTransactionPayload(
  params: TransactionParams,
  fromAddress: string,
  evmChain: string,
  deps: TransactionDependencies,
): Promise<PrepareERC20TransferResponse | PrepareNativeTransferResponse> {
  const { prepareERC20Transfer, prepareNativeTransfer } = deps;

  if (!params.native) {
    // ERC20 transfer
    const token = params.assetIdentifier;
    assert(token);

    const payload = {
      amount: params.amount,
      fromAddress,
      toAddress: params.to,
      token,
    };
    return prepareERC20Transfer(payload);
  }
  else {
    // Native token transfer
    const payload = {
      amount: params.amount,
      chain: evmChain,
      fromAddress,
      toAddress: params.to,
    };
    return {
      ...await prepareNativeTransfer(payload),
      data: '0x',
    };
  }
}

export function handleTransactionError(error: unknown, handlers: ErrorHandlers): void {
  const { setPreparing, setWaitingForWalletConfirmation, updateTransactionStatus } = handlers;

  setPreparing(false);
  setWaitingForWalletConfirmation(false);

  // If it's a transaction error with a hash, update its status
  if (error && typeof error === 'object' && 'transaction' in error
    && error.transaction && typeof error.transaction === 'object'
    && 'hash' in error.transaction && error.transaction.hash
    && typeof error.transaction.hash === 'string') {
    updateTransactionStatus(error.transaction.hash, 'failed');
  }
  console.error('Transaction failed:', error);
}
