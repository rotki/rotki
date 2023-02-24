import { Blockchain } from '@rotki/common/lib/blockchain';
import { type ActionResult } from '@rotki/common/lib/data';
import {
  type Eth2ValidatorEntry,
  Eth2Validators
} from '@rotki/common/lib/staking/eth2';
import { onlyIfTruthy } from '@rotki/common';
import { axiosSnakeCaseTransformer } from '@/services/axios-tranformers';
import { api } from '@/services/rotkehlchen-api';
import {
  type BtcAccountData,
  type GeneralAccountData,
  type PendingTask
} from '@/services/types-api';
import {
  handleResponse,
  validAuthorizedStatus,
  validWithParamsSessionAndExternalService,
  validWithSessionAndExternalService,
  validWithSessionStatus
} from '@/services/utils';
import {
  type BlockchainAccountPayload,
  type XpubPayload
} from '@/store/balances/types';
import { type BtcChains } from '@/types/blockchain/chains';
import { assert } from '@/utils/assertions';
import { type Eth2Validator } from '@/types/balances';
import { EvmAccountsResult } from '@/types/api/accounts';
import { nonEmptyProperties } from '@/utils/data';

const performAsyncQuery = async (
  url: string,
  payload: any
): Promise<PendingTask> => {
  const response = await api.instance.put<ActionResult<PendingTask>>(
    url,
    axiosSnakeCaseTransformer({
      asyncQuery: true,
      ...payload
    }),
    {
      validateStatus: validWithParamsSessionAndExternalService
    }
  );

  return handleResponse(response);
};

const payloadToData = ({
  address,
  label,
  tags
}: Omit<BlockchainAccountPayload, 'blockchain'>): {
  accounts: GeneralAccountData[];
} => ({
  accounts: [
    {
      address,
      label: label || null,
      tags
    }
  ]
});

export const useBlockchainAccountsApi = () => {
  const addBlockchainAccount = ({
    address,
    blockchain,
    label,
    tags,
    xpub
  }: BlockchainAccountPayload): Promise<PendingTask> => {
    const url = xpub
      ? `/blockchains/${blockchain}/xpub`
      : `/blockchains/${blockchain}/accounts`;

    const basePayload = {
      label: label || null,
      tags
    };

    const payload = xpub
      ? {
          xpub: xpub.xpub,
          derivationPath: onlyIfTruthy(xpub.derivationPath),
          xpubType: onlyIfTruthy(xpub.xpubType),
          ...basePayload
        }
      : {
          accounts: [
            {
              address,
              ...basePayload
            }
          ]
        };
    return performAsyncQuery(url, nonEmptyProperties(payload));
  };

  const removeBlockchainAccount = async (
    blockchain: string,
    accounts: string[]
  ): Promise<PendingTask> => {
    const response = await api.instance.delete<ActionResult<PendingTask>>(
      `/blockchains/${blockchain}/accounts`,
      {
        data: axiosSnakeCaseTransformer({
          asyncQuery: true,
          accounts
        }),
        validateStatus: validWithParamsSessionAndExternalService
      }
    );

    return handleResponse(response);
  };

  const editBtcAccount = async (
    payload: BlockchainAccountPayload
  ): Promise<BtcAccountData> => {
    const url = payload.xpub
      ? `/blockchains/${payload.blockchain}/xpub`
      : `/blockchains/${payload.blockchain}/accounts`;
    const { label, tags } = payload;

    let data: {};
    if (payload.xpub) {
      const { derivationPath, xpub } = payload.xpub;
      data = {
        xpub,
        derivationPath: onlyIfTruthy(derivationPath),
        label: label || null,
        tags
      };
    } else {
      data = payloadToData(payload);
    }

    const response = await api.instance.patch<ActionResult<BtcAccountData>>(
      url,
      axiosSnakeCaseTransformer(nonEmptyProperties(data)),
      {
        validateStatus: validWithParamsSessionAndExternalService
      }
    );

    return handleResponse(response);
  };

  const editBlockchainAccount = async (
    payload: BlockchainAccountPayload
  ): Promise<GeneralAccountData[]> => {
    const { blockchain } = payload;
    assert(
      ![Blockchain.BTC, Blockchain.BCH].includes(blockchain),
      'call editBtcAccount for btc'
    );
    const response = await api.instance.patch<
      ActionResult<GeneralAccountData[]>
    >(
      `/blockchains/${blockchain}/accounts`,
      nonEmptyProperties(payloadToData(payload)),
      {
        validateStatus: validWithParamsSessionAndExternalService
      }
    );

    return handleResponse(response);
  };

  const queryAccounts = async (
    blockchain: Exclude<Blockchain, BtcChains>
  ): Promise<GeneralAccountData[]> => {
    const response = await api.instance.get<ActionResult<GeneralAccountData[]>>(
      `/blockchains/${blockchain}/accounts`,
      {
        validateStatus: validWithSessionStatus
      }
    );
    return handleResponse(response);
  };

  const queryBtcAccounts = async (
    blockchain: BtcChains
  ): Promise<BtcAccountData> => {
    const response = await api.instance.get<ActionResult<BtcAccountData>>(
      `/blockchains/${blockchain}/accounts`,
      {
        validateStatus: validWithSessionStatus
      }
    );

    return handleResponse(response);
  };

  const deleteXpub = async ({
    blockchain,
    derivationPath,
    xpub
  }: XpubPayload): Promise<PendingTask> => {
    const response = await api.instance.delete<ActionResult<PendingTask>>(
      `/blockchains/${blockchain}/xpub`,
      {
        data: axiosSnakeCaseTransformer({
          xpub,
          derivationPath: derivationPath ? derivationPath : undefined,
          asyncQuery: true
        }),
        validateStatus: validWithParamsSessionAndExternalService
      }
    );

    return handleResponse(response);
  };

  const getEth2Validators = async (): Promise<Eth2Validators> => {
    const response = await api.instance.get<ActionResult<Eth2Validators>>(
      '/blockchains/ETH2/validators',
      {
        validateStatus: validWithSessionStatus
      }
    );
    const result = handleResponse(response);
    return Eth2Validators.parse(result);
  };

  const addEth2Validator = async (
    payload: Eth2Validator
  ): Promise<PendingTask> => {
    const response = await api.instance.put<ActionResult<PendingTask>>(
      '/blockchains/ETH2/validators',
      axiosSnakeCaseTransformer({ ...payload, asyncQuery: true }),
      {
        validateStatus: validAuthorizedStatus
      }
    );

    return handleResponse(response);
  };

  const deleteEth2Validators = async (
    validators: Eth2ValidatorEntry[]
  ): Promise<boolean> => {
    const response = await api.instance.delete<ActionResult<boolean>>(
      '/blockchains/ETH2/validators',
      {
        data: axiosSnakeCaseTransformer({
          validators
        }),
        validateStatus: validWithSessionStatus
      }
    );
    return handleResponse(response);
  };

  const editEth2Validator = async ({
    ownershipPercentage,
    validatorIndex
  }: Eth2Validator): Promise<boolean> => {
    const response = await api.instance.patch<ActionResult<boolean>>(
      '/blockchains/ETH2/validators',
      axiosSnakeCaseTransformer({ ownershipPercentage, validatorIndex }),
      {
        validateStatus: validWithSessionAndExternalService
      }
    );

    return handleResponse(response);
  };

  const addEvmAccount = async (
    payload: Omit<BlockchainAccountPayload, 'blockchain'>
  ): Promise<EvmAccountsResult> => {
    const response = await api.instance.put<ActionResult<EvmAccountsResult>>(
      '/blockchains/evm/accounts',
      nonEmptyProperties(payloadToData(payload)),
      {
        validateStatus: validWithParamsSessionAndExternalService
      }
    );
    return EvmAccountsResult.parse(handleResponse(response));
  };

  return {
    addBlockchainAccount,
    addEvmAccount,
    removeBlockchainAccount,
    editBlockchainAccount,
    editBtcAccount,
    queryAccounts,
    queryBtcAccounts,
    deleteXpub,
    getEth2Validators,
    addEth2Validator,
    editEth2Validator,
    deleteEth2Validators
  };
};
