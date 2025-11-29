import type { Eth2Validator } from '@/types/balances';
import { assert, type Eth2ValidatorEntry, Eth2Validators, type EthValidatorFilter, type Nullable, onlyIfTruthy } from '@rotki/common';
import { omit } from 'es-toolkit';
import { api } from '@/modules/api/rotki-api';
import {
  VALID_WITH_PARAMS_SESSION_AND_EXTERNAL_SERVICE,
  VALID_WITH_SESSION_AND_EXTERNAL_SERVICE,
  VALID_WITH_SESSION_STATUS,
} from '@/modules/api/utils';
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
import { type PendingTask, PendingTaskSchema } from '@/types/task';

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
    const response = await api.put<PendingTask>(
      url,
      { asyncQuery: true, ...payload },
      {
        filterEmptyProperties: { removeEmptyString: true },
        validStatuses: VALID_WITH_PARAMS_SESSION_AND_EXTERNAL_SERVICE,
      },
    );
    return PendingTaskSchema.parse(response);
  };

  const removeBlockchainAccount = async (blockchain: string, accounts: string[]): Promise<PendingTask> => {
    const response = await api.delete<PendingTask>(`/blockchains/${blockchain}/accounts`, {
      body: {
        accounts,
        asyncQuery: true,
      },
      validStatuses: VALID_WITH_PARAMS_SESSION_AND_EXTERNAL_SERVICE,
    });
    return PendingTaskSchema.parse(response);
  };

  const removeAgnosticBlockchainAccount = async (chainType: string, accounts: string[]): Promise<PendingTask> => {
    const response = await api.delete<PendingTask>(`/blockchains/type/${chainType}/accounts`, {
      body: {
        accounts,
        asyncQuery: true,
      },
      validStatuses: VALID_WITH_PARAMS_SESSION_AND_EXTERNAL_SERVICE,
    });
    return PendingTaskSchema.parse(response);
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

    const response = await api.patch<BitcoinAccounts>(
      url,
      data,
      {
        filterEmptyProperties: true,
        validStatuses: VALID_WITH_PARAMS_SESSION_AND_EXTERNAL_SERVICE,
      },
    );

    return BitcoinAccounts.parse(response);
  };

  const editBlockchainAccount = async (payload: AccountPayload, chain: string): Promise<BlockchainAccounts> => {
    assert(!isBtcChain(chain), 'call editBtcAccount for btc');
    const response = await api.patch<GeneralAccountData[]>(
      `/blockchains/${chain}/accounts`,
      payloadToData(payload),
      {
        filterEmptyProperties: true,
        validStatuses: VALID_WITH_PARAMS_SESSION_AND_EXTERNAL_SERVICE,
      },
    );

    return BlockchainAccounts.parse(response);
  };

  const editAgnosticBlockchainAccount = async (chainType: string, payload: AccountPayload): Promise<boolean> => api.patch<boolean>(
    `/blockchains/type/${chainType}/accounts`,
    payloadToData(payload),
    {
      filterEmptyProperties: true,
      validStatuses: VALID_WITH_PARAMS_SESSION_AND_EXTERNAL_SERVICE,
    },
  );

  const queryAccounts = async (blockchain: string): Promise<BlockchainAccounts> => {
    const response = await api.get<BlockchainAccounts>(
      `/blockchains/${blockchain}/accounts`,
      {
        validStatuses: VALID_WITH_SESSION_STATUS,
      },
    );
    return BlockchainAccounts.parse(response);
  };

  const queryBtcAccounts = async (blockchain: BtcChains): Promise<BitcoinAccounts> => {
    const response = await api.get<BitcoinAccounts>(`/blockchains/${blockchain}/accounts`, {
      validStatuses: VALID_WITH_SESSION_STATUS,
    });

    return BitcoinAccounts.parse(response);
  };

  const deleteXpub = async ({ chain, derivationPath, xpub }: DeleteXpubParams): Promise<PendingTask> => {
    const response = await api.delete<PendingTask>(`/blockchains/${chain}/xpub`, {
      body: {
        asyncQuery: true,
        derivationPath: derivationPath || undefined,
        xpub,
      },
      validStatuses: VALID_WITH_PARAMS_SESSION_AND_EXTERNAL_SERVICE,
    });
    return PendingTaskSchema.parse(response);
  };

  const getEth2Validators = async (payload: EthValidatorFilter = { }): Promise<Eth2Validators> => {
    const response = await api.get<Eth2Validators>('/blockchains/eth2/validators', {
      filterEmptyProperties: true,
      query: payload,
      validStatuses: VALID_WITH_SESSION_STATUS,
    });
    return Eth2Validators.parse(response);
  };

  const addEth2Validator = async (payload: Eth2Validator): Promise<PendingTask> => {
    const response = await api.put<PendingTask>(
      '/blockchains/eth2/validators',
      { ...payload, asyncQuery: true },
      {
        filterEmptyProperties: { removeEmptyString: true },
      },
    );
    return PendingTaskSchema.parse(response);
  };

  const deleteEth2Validators = async (validators: Eth2ValidatorEntry[]): Promise<boolean> => api.delete<boolean>('/blockchains/eth2/validators', {
    body: {
      validators: validators.map(({ index }) => index),
    },
    validStatuses: VALID_WITH_SESSION_STATUS,
  });

  const editEth2Validator = async ({ ownershipPercentage, validatorIndex }: Eth2Validator): Promise<boolean> => api.patch<boolean>(
    '/blockchains/eth2/validators',
    { ownershipPercentage, validatorIndex },
    {
      validStatuses: VALID_WITH_SESSION_AND_EXTERNAL_SERVICE,
    },
  );

  const addEvmAccount = async (payload: Omit<BlockchainAccountPayload, 'blockchain'>): Promise<PendingTask> => {
    const response = await api.put<PendingTask>(
      '/blockchains/evm/accounts',
      { asyncQuery: true, ...payloadToData(payload, true) },
      {
        filterEmptyProperties: true,
        validStatuses: VALID_WITH_PARAMS_SESSION_AND_EXTERNAL_SERVICE,
      },
    );
    return PendingTaskSchema.parse(response);
  };

  const detectEvmAccounts = async (): Promise<PendingTask> => {
    const response = await api.post<PendingTask>(
      '/blockchains/evm/accounts',
      {
        asyncQuery: true,
      },
      {
        validStatuses: VALID_WITH_SESSION_AND_EXTERNAL_SERVICE,
      },
    );
    return PendingTaskSchema.parse(response);
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
