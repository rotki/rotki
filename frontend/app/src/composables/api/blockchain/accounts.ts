import type { Eth2Validator } from '@/types/balances';
import type { PendingTask } from '@/types/task';
import { type ActionResult, assert, type Eth2ValidatorEntry, Eth2Validators, type EthValidatorFilter, type Nullable, onlyIfTruthy } from '@rotki/common';
import { omit } from 'es-toolkit';
import { snakeCaseTransformer } from '@/services/axios-transformers';
import { api } from '@/services/rotkehlchen-api';
import {
  handleResponse,
  paramsSerializer,
  validAuthorizedStatus,
  validWithParamsSessionAndExternalService,
  validWithSessionAndExternalService,
  validWithSessionStatus,
} from '@/services/utils';
import {
  type AccountPayload,
  BitcoinAccounts,
  type BlockchainAccountPayload,
  BlockchainAccounts,
  type DeleteXpubParams,
  type GeneralAccountData,
  type XpubAccountPayload,
} from '@/types/blockchain/accounts';
import { type BtcChains, isBtcChain } from '@/types/blockchain/chains';
import { nonEmptyProperties } from '@/utils/data';

async function performAsyncQuery(url: string, payload: any): Promise<PendingTask> {
  const response = await api.instance.put<ActionResult<PendingTask>>(
    url,
    snakeCaseTransformer({
      asyncQuery: true,
      ...payload,
    }),
    {
      validateStatus: validWithParamsSessionAndExternalService,
    },
  );

  return handleResponse(response);
}

function payloadToData({ address, label, tags }: Omit<BlockchainAccountPayload, 'blockchain'>, isAdd = false): {
  accounts: GeneralAccountData[];
} {
  const usedLabel = isAdd ? (label || null) : (label ?? null);

  return {
    accounts: [
      {
        address,
        label: usedLabel,
        tags,
      },
    ],
  };
}

interface UseBlockchainAccountsApiReturn {
  addBlockchainAccount: (chain: string, pay: XpubAccountPayload | AccountPayload[]) => Promise<PendingTask>;
  addEvmAccount: (payload: Omit<BlockchainAccountPayload, 'blockchain'>) => Promise<PendingTask>;
  detectEvmAccounts: () => Promise<PendingTask>;
  removeAgnosticBlockchainAccount: (chainType: string, accounts: string[]) => Promise<PendingTask>;
  removeBlockchainAccount: (blockchain: string, accounts: string[]) => Promise<PendingTask>;
  editBlockchainAccount: (payload: AccountPayload, chain: string) => Promise<BlockchainAccounts>;
  editAgnosticBlockchainAccount: (chainType: string, payload: AccountPayload) => Promise<boolean>;
  editBtcAccount: (payload: AccountPayload | XpubAccountPayload, chain: string) => Promise<BitcoinAccounts>;
  queryAccounts: (blockchain: string) => Promise<BlockchainAccounts>;
  queryBtcAccounts: (blockchain: BtcChains) => Promise<BitcoinAccounts>;
  deleteXpub: ({ chain, derivationPath, xpub }: DeleteXpubParams) => Promise<PendingTask>;
  getEth2Validators: (payload?: EthValidatorFilter) => Promise<Eth2Validators>;
  addEth2Validator: (payload: Eth2Validator) => Promise<PendingTask>;
  editEth2Validator: ({ ownershipPercentage, validatorIndex }: Eth2Validator) => Promise<boolean>;
  deleteEth2Validators: (validators: Eth2ValidatorEntry[]) => Promise<boolean>;
}

export function useBlockchainAccountsApi(): UseBlockchainAccountsApiReturn {
  const addBlockchainAccount = async (chain: string, pay: XpubAccountPayload | AccountPayload[]): Promise<PendingTask> => {
    const url = !Array.isArray(pay) ? `/blockchains/${chain}/xpub` : `/blockchains/${chain}/accounts`;
    const payload = Array.isArray(pay) ? { accounts: pay } : { ...omit(pay, ['xpub']), ...pay.xpub };
    return performAsyncQuery(url, nonEmptyProperties(payload, {
      removeEmptyString: true,
    }));
  };

  const removeBlockchainAccount = async (blockchain: string, accounts: string[]): Promise<PendingTask> => {
    const response = await api.instance.delete<ActionResult<PendingTask>>(`/blockchains/${blockchain}/accounts`, {
      data: snakeCaseTransformer({
        accounts,
        asyncQuery: true,
      }),
      validateStatus: validWithParamsSessionAndExternalService,
    });

    return handleResponse(response);
  };

  const removeAgnosticBlockchainAccount = async (chainType: string, accounts: string[]): Promise<PendingTask> => {
    const response = await api.instance.delete<ActionResult<PendingTask>>(`/blockchains/type/${chainType}/accounts`, {
      data: snakeCaseTransformer({
        accounts,
        asyncQuery: true,
      }),
      validateStatus: validWithParamsSessionAndExternalService,
    });

    return handleResponse(response);
  };

  const editBtcAccount = async (
    payload: AccountPayload | XpubAccountPayload,
    chain: string,
  ): Promise<BitcoinAccounts> => {
    const url = 'xpub' in payload ? `/blockchains/${chain}/xpub` : `/blockchains/${chain}/accounts`;
    const { label, tags } = payload;

    let data:
      | { accounts: GeneralAccountData[] }
      | {
        xpub: string;
        derivationPath?: string;
        label: Nullable<string>;
        tags: Nullable<string[]>;
      };
    if ('xpub' in payload) {
      const { derivationPath, xpub } = payload.xpub;
      data = {
        derivationPath: onlyIfTruthy(derivationPath),
        label: label || null,
        tags,
        xpub,
      };
    }
    else {
      data = payloadToData(payload);
    }

    const response = await api.instance.patch<ActionResult<BitcoinAccounts>>(
      url,
      snakeCaseTransformer(nonEmptyProperties(data)),
      {
        validateStatus: validWithParamsSessionAndExternalService,
      },
    );

    return BitcoinAccounts.parse(handleResponse(response));
  };

  const editBlockchainAccount = async (payload: AccountPayload, chain: string): Promise<BlockchainAccounts> => {
    assert(!isBtcChain(chain), 'call editBtcAccount for btc');
    const response = await api.instance.patch<ActionResult<GeneralAccountData[]>>(
      `/blockchains/${chain}/accounts`,
      nonEmptyProperties(payloadToData(payload)),
      {
        validateStatus: validWithParamsSessionAndExternalService,
      },
    );

    return BlockchainAccounts.parse(handleResponse(response));
  };

  const editAgnosticBlockchainAccount = async (chainType: string, payload: AccountPayload): Promise<boolean> => {
    const response = await api.instance.patch<ActionResult<boolean>>(
      `/blockchains/type/${chainType}/accounts`,
      {
        ...nonEmptyProperties(payloadToData(payload)),
      },
      {
        validateStatus: validWithParamsSessionAndExternalService,
      },
    );

    return handleResponse(response);
  };

  const queryAccounts = async (blockchain: string): Promise<BlockchainAccounts> => {
    const response = await api.instance.get<ActionResult<BlockchainAccounts>>(
      `/blockchains/${blockchain}/accounts`,
      {
        validateStatus: validWithSessionStatus,
      },
    );
    return BlockchainAccounts.parse(handleResponse(response));
  };

  const queryBtcAccounts = async (blockchain: BtcChains): Promise<BitcoinAccounts> => {
    const response = await api.instance.get<ActionResult<BitcoinAccounts>>(`/blockchains/${blockchain}/accounts`, {
      validateStatus: validWithSessionStatus,
    });

    return BitcoinAccounts.parse(handleResponse(response));
  };

  const deleteXpub = async ({ chain, derivationPath, xpub }: DeleteXpubParams): Promise<PendingTask> => {
    const response = await api.instance.delete<ActionResult<PendingTask>>(`/blockchains/${chain}/xpub`, {
      data: snakeCaseTransformer({
        asyncQuery: true,
        derivationPath: derivationPath || undefined,
        xpub,
      }),
      validateStatus: validWithParamsSessionAndExternalService,
    });

    return handleResponse(response);
  };

  const getEth2Validators = async (payload: EthValidatorFilter = { }): Promise<Eth2Validators> => {
    const response = await api.instance.get<ActionResult<Eth2Validators>>('/blockchains/eth2/validators', {
      params: snakeCaseTransformer(nonEmptyProperties(payload)),
      paramsSerializer,
      validateStatus: validWithSessionStatus,
    });
    const result = handleResponse(response);
    return Eth2Validators.parse(result);
  };

  const addEth2Validator = async (payload: Eth2Validator): Promise<PendingTask> => {
    const response = await api.instance.put<ActionResult<PendingTask>>(
      '/blockchains/eth2/validators',
      snakeCaseTransformer({ ...nonEmptyProperties(payload, {
        removeEmptyString: true,
      }), asyncQuery: true }),
      {
        validateStatus: validAuthorizedStatus,
      },
    );

    return handleResponse(response);
  };

  const deleteEth2Validators = async (validators: Eth2ValidatorEntry[]): Promise<boolean> => {
    const response = await api.instance.delete<ActionResult<boolean>>('/blockchains/eth2/validators', {
      data: snakeCaseTransformer({
        validators: validators.map(({ index }) => index),
      }),
      validateStatus: validWithSessionStatus,
    });
    return handleResponse(response);
  };

  const editEth2Validator = async ({ ownershipPercentage, validatorIndex }: Eth2Validator): Promise<boolean> => {
    const response = await api.instance.patch<ActionResult<boolean>>(
      '/blockchains/eth2/validators',
      snakeCaseTransformer({ ownershipPercentage, validatorIndex }),
      {
        validateStatus: validWithSessionAndExternalService,
      },
    );

    return handleResponse(response);
  };

  const addEvmAccount = async (payload: Omit<BlockchainAccountPayload, 'blockchain'>): Promise<PendingTask> =>
    performAsyncQuery('/blockchains/evm/accounts', nonEmptyProperties(payloadToData(payload, true)));

  const detectEvmAccounts = async (): Promise<PendingTask> => {
    const response = await api.instance.post<ActionResult<PendingTask>>(
      '/blockchains/evm/accounts',
      snakeCaseTransformer({
        asyncQuery: true,
      }),
      {
        validateStatus: validWithSessionAndExternalService,
      },
    );

    return handleResponse(response);
  };

  return {
    addBlockchainAccount,
    addEth2Validator,
    addEvmAccount,
    deleteEth2Validators,
    deleteXpub,
    detectEvmAccounts,
    editAgnosticBlockchainAccount,
    editBlockchainAccount,
    editBtcAccount,
    editEth2Validator,
    getEth2Validators,
    queryAccounts,
    queryBtcAccounts,
    removeAgnosticBlockchainAccount,
    removeBlockchainAccount,
  };
}
