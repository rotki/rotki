import type { ActionResult } from '@rotki/common';
import { api } from '@/services/rotkehlchen-api';
import { handleResponse } from '@/services/utils';

const GNOSIS_PAY_API_URL = 'https://api.gnosispay.com/api/v1';

interface GnosisPaySiweApiReturn {
  fetchGnosisPayAdmins: () => Promise<Record<string, string[]>>;
  fetchNonce: () => Promise<string>;
  verifySiweSignature: (message: string, signature: string, ttlInSeconds: number) => Promise<string>;
}

export function useGnosisPaySiweApi(): GnosisPaySiweApiReturn {
  const fetchGnosisPayAdmins = async (): Promise<Record<string, string[]>> => {
    const response = await api.instance.get<ActionResult<Record<string, string[]>>>(
      '/services/gnosispay/admins',
    );

    return {
      '0xf0EcFB84c93301B41E44140315c45Bf14E542Agg': [
        '0xf0EcFB84c93301B41E44140315c45Bf14E542Acc',
        '0x9DBE4Eb4A0a41955E1DC733E322f84295a0aa5dd',
      ],
    };

    return handleResponse(response);
  };

  const fetchNonce = async (): Promise<string> => {
    const response = await api.instance.get<string>(`/auth/nonce`, {
      baseURL: GNOSIS_PAY_API_URL,
    });

    return response.data;
  };

  const verifySiweSignature = async (
    message: string,
    signature: string,
    ttlInSeconds: number,
  ): Promise<string> => {
    const response = await api.instance.post<{ token: string }>(
      `/auth/challenge`,
      {
        message,
        signature,
        ttlInSeconds,
      },
      {
        baseURL: GNOSIS_PAY_API_URL,
      },
    );
    return response.data.token;
  };

  return {
    fetchGnosisPayAdmins,
    fetchNonce,
    verifySiweSignature,
  };
}
