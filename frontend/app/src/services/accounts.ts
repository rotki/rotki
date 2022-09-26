import { Blockchain } from '@rotki/common/lib/blockchain';
import { ActionResult } from '@rotki/common/lib/data';
import { axiosSnakeCaseTransformer } from '@/services/axios-tranformers';
import { basicAxiosTransformer } from '@/services/consts';
import { api } from '@/services/rotkehlchen-api';
import {
  BtcAccountData,
  GeneralAccountData,
  PendingTask
} from '@/services/types-api';
import {
  handleResponse,
  validWithParamsSessionAndExternalService,
  validWithSessionStatus
} from '@/services/utils';
import { BlockchainAccountPayload, XpubPayload } from '@/store/balances/types';
import { BtcChains } from '@/types/blockchain/chains';
import { assert } from '@/utils/assertions';

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
      validateStatus: validWithParamsSessionAndExternalService,
      transformResponse: basicAxiosTransformer
    }
  );

  return handleResponse(response);
};

const payloadToData = ({
  address,
  label,
  tags
}: BlockchainAccountPayload): { accounts: GeneralAccountData[] } => ({
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
      : `/blockchains/${blockchain}`;

    const basePayload = {
      label: label || null,
      tags
    };

    const payload = xpub
      ? {
          xpub: xpub.xpub,
          derivationPath: xpub.derivationPath ? xpub.derivationPath : undefined,
          xpubType: xpub.xpubType ? xpub.xpubType : undefined,
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
    return performAsyncQuery(url, payload);
  };

  const removeBlockchainAccount = async (
    blockchain: string,
    accounts: string[]
  ): Promise<PendingTask> => {
    const response = await api.instance.delete<ActionResult<PendingTask>>(
      `/blockchains/${blockchain}`,
      {
        data: axiosSnakeCaseTransformer({
          asyncQuery: true,
          accounts: accounts
        }),
        validateStatus: validWithParamsSessionAndExternalService,
        transformResponse: basicAxiosTransformer
      }
    );

    return handleResponse(response);
  };

  const editBtcAccount = async (
    payload: BlockchainAccountPayload
  ): Promise<BtcAccountData> => {
    let url = `/blockchains/${payload.blockchain}`;
    const { label, tags } = payload;

    let data: {};
    if (payload.xpub && !payload.address) {
      url += '/xpub';
      const { derivationPath, xpub } = payload.xpub;
      data = {
        xpub,
        derivationPath: derivationPath ? derivationPath : undefined,
        label: label || null,
        tags
      };
    } else {
      data = payloadToData(payload);
    }

    const response = await api.instance.patch<ActionResult<BtcAccountData>>(
      url,
      axiosSnakeCaseTransformer(data),
      {
        validateStatus: validWithParamsSessionAndExternalService,
        transformResponse: basicAxiosTransformer
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
    >(`/blockchains/${blockchain}`, payloadToData(payload), {
      validateStatus: validWithParamsSessionAndExternalService,
      transformResponse: basicAxiosTransformer
    });

    return handleResponse(response);
  };

  const queryAccounts = async (
    blockchain: Exclude<Blockchain, BtcChains>
  ): Promise<GeneralAccountData[]> => {
    const response = await api.instance.get<ActionResult<GeneralAccountData[]>>(
      `/blockchains/${blockchain}`,
      {
        validateStatus: validWithSessionStatus,
        transformResponse: basicAxiosTransformer
      }
    );
    return handleResponse(response);
  };

  const queryBtcAccounts = async (
    blockchain: BtcChains
  ): Promise<BtcAccountData> => {
    const response = await api.instance.get<ActionResult<BtcAccountData>>(
      `/blockchains/${blockchain}`,
      {
        validateStatus: validWithSessionStatus,
        transformResponse: basicAxiosTransformer
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
        validateStatus: validWithParamsSessionAndExternalService,
        transformResponse: basicAxiosTransformer
      }
    );

    return handleResponse(response);
  };

  return {
    addBlockchainAccount,
    removeBlockchainAccount,
    editBlockchainAccount,
    editBtcAccount,
    queryAccounts,
    queryBtcAccounts,
    deleteXpub
  };
};
