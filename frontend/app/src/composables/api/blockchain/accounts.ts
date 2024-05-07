import {
  type Eth2ValidatorEntry,
  Eth2Validators,
  type EthValidatorFilter,
} from '@rotki/common/lib/staking/eth2';
import { type Nullable, onlyIfTruthy } from '@rotki/common';
import { snakeCaseTransformer } from '@/services/axios-tranformers';
import { api } from '@/services/rotkehlchen-api';
import {
  handleResponse,
  paramsSerializer,
  validAuthorizedStatus,
  validWithParamsSessionAndExternalService,
  validWithSessionAndExternalService,
  validWithSessionStatus,
} from '@/services/utils';
import { type BtcChains, isBtcChain } from '@/types/blockchain/chains';
import {
  type AccountPayload,
  BitcoinAccounts,
  type BlockchainAccountPayload,
  BlockchainAccounts,
  type DeleteXpubParams,
  type GeneralAccountData,
  type XpubAccountPayload,
} from '@/types/blockchain/accounts';
import type { ActionResult } from '@rotki/common/lib/data';
import type { Eth2Validator } from '@/types/balances';
import type { PendingTask } from '@/types/task';

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

function payloadToData({
  address,
  label,
  tags,
}: Omit<BlockchainAccountPayload, 'blockchain'>): {
    accounts: GeneralAccountData[];
  } {
  return {
    accounts: [
      {
        address,
        label: label || null,
        tags,
      },
    ],
  };
}

export function useBlockchainAccountsApi() {
  const addBlockchainAccount = (chain: string, pay: XpubAccountPayload | AccountPayload[]): Promise<PendingTask> => {
    const url = !Array.isArray(pay)
      ? `/blockchains/${chain}/xpub`
      : `/blockchains/${chain}/accounts`;
    const payload = (Array.isArray(pay)) ? { accounts: pay } : pay;
    return performAsyncQuery(url, nonEmptyProperties(payload));
  };

  const removeBlockchainAccount = async (
    blockchain: string,
    accounts: string[],
  ): Promise<PendingTask> => {
    const response = await api.instance.delete<ActionResult<PendingTask>>(
      `/blockchains/${blockchain}/accounts`,
      {
        data: snakeCaseTransformer({
          asyncQuery: true,
          accounts,
        }),
        validateStatus: validWithParamsSessionAndExternalService,
      },
    );

    return handleResponse(response);
  };

  const editBtcAccount = async (
    payload: AccountPayload | XpubAccountPayload,
    chain: string,
  ): Promise<BitcoinAccounts> => {
    const url = 'xpub' in payload
      ? `/blockchains/${chain}/xpub`
      : `/blockchains/${chain}/accounts`;
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
        xpub,
        derivationPath: onlyIfTruthy(derivationPath),
        label: label || null,
        tags,
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

  const editBlockchainAccount = async (
    payload: AccountPayload,
    chain: string,
  ): Promise<BlockchainAccounts> => {
    assert(!isBtcChain(chain), 'call editBtcAccount for btc');
    const response = await api.instance.patch<
      ActionResult<GeneralAccountData[]>
    >(
      `/blockchains/${chain}/accounts`,
      nonEmptyProperties(payloadToData(payload)),
      {
        validateStatus: validWithParamsSessionAndExternalService,
      },
    );

    return BlockchainAccounts.parse(handleResponse(response));
  };

  const queryAccounts = async (
    blockchain: string,
  ): Promise<BlockchainAccounts> => {
    const response = await api.instance.get<ActionResult<BlockchainAccounts>>(
      `/blockchains/${blockchain.toString()}/accounts`,
      {
        validateStatus: validWithSessionStatus,
      },
    );
    return BlockchainAccounts.parse(handleResponse(response));
  };

  const queryBtcAccounts = async (
    blockchain: BtcChains,
  ): Promise<BitcoinAccounts> => {
    const response = await api.instance.get<ActionResult<BitcoinAccounts>>(
      `/blockchains/${blockchain}/accounts`,
      {
        validateStatus: validWithSessionStatus,
      },
    );

    return BitcoinAccounts.parse(handleResponse(response));
  };

  const deleteXpub = async ({
    chain,
    derivationPath,
    xpub,
  }: DeleteXpubParams): Promise<PendingTask> => {
    const response = await api.instance.delete<ActionResult<PendingTask>>(
      `/blockchains/${chain}/xpub`,
      {
        data: snakeCaseTransformer({
          xpub,
          derivationPath: derivationPath || undefined,
          asyncQuery: true,
        }),
        validateStatus: validWithParamsSessionAndExternalService,
      },
    );

    return handleResponse(response);
  };

  const getEth2Validators = async (payload: EthValidatorFilter = {}): Promise<Eth2Validators> => {
    const response = await api.instance.get<ActionResult<Eth2Validators>>(
      '/blockchains/eth2/validators',
      {
        params: snakeCaseTransformer(nonEmptyProperties(payload)),
        validateStatus: validWithSessionStatus,
        paramsSerializer,
      },
    );
    const result = handleResponse(response);
    return Eth2Validators.parse(result);
  };

  const addEth2Validator = async (
    payload: Eth2Validator,
  ): Promise<PendingTask> => {
    const response = await api.instance.put<ActionResult<PendingTask>>(
      '/blockchains/eth2/validators',
      snakeCaseTransformer({ ...payload, asyncQuery: true }),
      {
        validateStatus: validAuthorizedStatus,
      },
    );

    return handleResponse(response);
  };

  const deleteEth2Validators = async (
    validators: Eth2ValidatorEntry[],
  ): Promise<boolean> => {
    const response = await api.instance.delete<ActionResult<boolean>>(
      '/blockchains/eth2/validators',
      {
        data: snakeCaseTransformer({
          validators: validators.map(({ index }) => index),
        }),
        validateStatus: validWithSessionStatus,
      },
    );
    return handleResponse(response);
  };

  const editEth2Validator = async ({
    ownershipPercentage,
    validatorIndex,
  }: Eth2Validator): Promise<boolean> => {
    const response = await api.instance.patch<ActionResult<boolean>>(
      '/blockchains/eth2/validators',
      snakeCaseTransformer({ ownershipPercentage, validatorIndex }),
      {
        validateStatus: validWithSessionAndExternalService,
      },
    );

    return handleResponse(response);
  };

  const addEvmAccount = (
    payload: Omit<BlockchainAccountPayload, 'blockchain'>,
  ): Promise<PendingTask> => performAsyncQuery(
    '/blockchains/evm/accounts',
    nonEmptyProperties(payloadToData(payload)),
  );

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
    addEvmAccount,
    detectEvmAccounts,
    removeBlockchainAccount,
    editBlockchainAccount,
    editBtcAccount,
    queryAccounts,
    queryBtcAccounts,
    deleteXpub,
    getEth2Validators,
    addEth2Validator,
    editEth2Validator,
    deleteEth2Validators,
  };
}
