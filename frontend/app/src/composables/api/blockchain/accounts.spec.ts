import type { Eth2Validator } from '@/types/balances';
import { Blockchain, type Eth2ValidatorEntry, type EthValidatorFilter } from '@rotki/common';
import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { type AccountPayload, type DeleteXpubParams, type XpubAccountPayload, XpubKeyType } from '@/types/blockchain/accounts';
import { useBlockchainAccountsApi } from './accounts';

const backendUrl = process.env.VITE_BACKEND_URL;

describe('composables/api/blockchain/accounts', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('addBlockchainAccount', () => {
    it('adds accounts with PUT request to accounts endpoint', async () => {
      let capturedBody: Record<string, unknown> | null = null;
      let capturedUrl = '';

      server.use(
        http.put(`${backendUrl}/api/1/blockchains/:chain/accounts`, async ({ request }) => {
          capturedUrl = request.url;
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: { task_id: 123 },
            message: '',
          });
        }),
      );

      const { addBlockchainAccount } = useBlockchainAccountsApi();
      const accounts: AccountPayload[] = [
        { address: '0x1234567890123456789012345678901234567890', label: 'Test', tags: ['tag1'] },
      ];
      const result = await addBlockchainAccount('eth', accounts);

      expect(capturedUrl).toContain('/blockchains/eth/accounts');
      expect(capturedBody).toEqual({
        async_query: true,
        accounts: [
          { address: '0x1234567890123456789012345678901234567890', label: 'Test', tags: ['tag1'] },
        ],
      });
      expect(result.taskId).toBe(123);
    });

    it('adds xpub with PUT request to xpub endpoint', async () => {
      let capturedBody: Record<string, unknown> | null = null;
      let capturedUrl = '';

      server.use(
        http.put(`${backendUrl}/api/1/blockchains/:chain/xpub`, async ({ request }) => {
          capturedUrl = request.url;
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: { task_id: 456 },
            message: '',
          });
        }),
      );

      const { addBlockchainAccount } = useBlockchainAccountsApi();
      const xpubPayload: XpubAccountPayload = {
        xpub: {
          xpub: 'xpub6CUGRUo...',
          derivationPath: 'm/44\'/0\'/0\'',
          xpubType: XpubKeyType.XPUB,
        },
        label: 'My Xpub',
        tags: ['bitcoin'],
      };
      const result = await addBlockchainAccount('btc', xpubPayload);

      expect(capturedUrl).toContain('/blockchains/btc/xpub');
      expect(capturedBody).toEqual({
        async_query: true,
        xpub: 'xpub6CUGRUo...',
        derivation_path: 'm/44\'/0\'/0\'',
        xpub_type: XpubKeyType.XPUB,
        label: 'My Xpub',
        tags: ['bitcoin'],
      });
      expect(result.taskId).toBe(456);
    });

    it('throws error on failure', async () => {
      server.use(
        http.put(`${backendUrl}/api/1/blockchains/:chain/accounts`, () =>
          HttpResponse.json({
            result: null,
            message: 'Invalid account address',
          })),
      );

      const { addBlockchainAccount } = useBlockchainAccountsApi();

      await expect(addBlockchainAccount('eth', [{ address: 'invalid', tags: null }]))
        .rejects
        .toThrow('Invalid account address');
    });
  });

  describe('addEvmAccount', () => {
    it('adds EVM account with PUT request', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.put(`${backendUrl}/api/1/blockchains/evm/accounts`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: { task_id: 789 },
            message: '',
          });
        }),
      );

      const { addEvmAccount } = useBlockchainAccountsApi();
      const result = await addEvmAccount({
        address: '0xABCDEF1234567890123456789012345678901234',
        label: 'EVM Account',
        tags: ['evm'],
      });

      expect(capturedBody).toEqual({
        async_query: true,
        accounts: [
          {
            address: '0xABCDEF1234567890123456789012345678901234',
            label: 'EVM Account',
            tags: ['evm'],
          },
        ],
      });
      expect(result.taskId).toBe(789);
    });

    it('handles account without label', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.put(`${backendUrl}/api/1/blockchains/evm/accounts`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: { task_id: 101 },
            message: '',
          });
        }),
      );

      const { addEvmAccount } = useBlockchainAccountsApi();
      await addEvmAccount({
        address: '0x1234567890123456789012345678901234567890',
        tags: null,
      });

      // nonEmptyProperties removes null/empty values
      expect(capturedBody).toEqual({
        async_query: true,
        accounts: [
          {
            address: '0x1234567890123456789012345678901234567890',
          },
        ],
      });
    });
  });

  describe('detectEvmAccounts', () => {
    it('sends POST request to detect EVM accounts', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.post(`${backendUrl}/api/1/blockchains/evm/accounts`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: { task_id: 111 },
            message: '',
          });
        }),
      );

      const { detectEvmAccounts } = useBlockchainAccountsApi();
      const result = await detectEvmAccounts();

      expect(capturedBody).toEqual({
        async_query: true,
      });
      expect(result.taskId).toBe(111);
    });
  });

  describe('removeBlockchainAccount', () => {
    it('sends DELETE request with accounts in body', async () => {
      let capturedBody: Record<string, unknown> | null = null;
      let capturedUrl = '';

      server.use(
        http.delete(`${backendUrl}/api/1/blockchains/:chain/accounts`, async ({ request }) => {
          capturedUrl = request.url;
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: { task_id: 222 },
            message: '',
          });
        }),
      );

      const { removeBlockchainAccount } = useBlockchainAccountsApi();
      const result = await removeBlockchainAccount('eth', ['0x123', '0x456']);

      expect(capturedUrl).toContain('/blockchains/eth/accounts');
      expect(capturedBody).toEqual({
        accounts: ['0x123', '0x456'],
        async_query: true,
      });
      expect(result.taskId).toBe(222);
    });

    it('throws error on failure', async () => {
      server.use(
        http.delete(`${backendUrl}/api/1/blockchains/:chain/accounts`, () =>
          HttpResponse.json({
            result: null,
            message: 'Account not found',
          })),
      );

      const { removeBlockchainAccount } = useBlockchainAccountsApi();

      await expect(removeBlockchainAccount('eth', ['0xunknown']))
        .rejects
        .toThrow('Account not found');
    });
  });

  describe('removeAgnosticBlockchainAccount', () => {
    it('sends DELETE request to chain type endpoint', async () => {
      let capturedBody: Record<string, unknown> | null = null;
      let capturedUrl = '';

      server.use(
        http.delete(`${backendUrl}/api/1/blockchains/type/:chainType/accounts`, async ({ request }) => {
          capturedUrl = request.url;
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: { task_id: 333 },
            message: '',
          });
        }),
      );

      const { removeAgnosticBlockchainAccount } = useBlockchainAccountsApi();
      const result = await removeAgnosticBlockchainAccount('evm', ['0x123']);

      expect(capturedUrl).toContain('/blockchains/type/evm/accounts');
      expect(capturedBody).toEqual({
        accounts: ['0x123'],
        async_query: true,
      });
      expect(result.taskId).toBe(333);
    });
  });

  describe('editBlockchainAccount', () => {
    it('sends PATCH request with account data', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.patch(`${backendUrl}/api/1/blockchains/:chain/accounts`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: [
              {
                address: '0x1234567890123456789012345678901234567890',
                label: 'Updated Label',
                tags: ['updated'],
              },
            ],
            message: '',
          });
        }),
      );

      const { editBlockchainAccount } = useBlockchainAccountsApi();
      const payload: AccountPayload = {
        address: '0x1234567890123456789012345678901234567890',
        label: 'Updated Label',
        tags: ['updated'],
      };
      const result = await editBlockchainAccount(payload, 'eth');

      expect(capturedBody).toEqual({
        accounts: [
          {
            address: '0x1234567890123456789012345678901234567890',
            label: 'Updated Label',
            tags: ['updated'],
          },
        ],
      });
      expect(result).toHaveLength(1);
      expect(result[0].label).toBe('Updated Label');
    });

    it('throws error on failure', async () => {
      server.use(
        http.patch(`${backendUrl}/api/1/blockchains/:chain/accounts`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to update account',
          })),
      );

      const { editBlockchainAccount } = useBlockchainAccountsApi();

      await expect(editBlockchainAccount({ address: '0x123', tags: null }, 'eth'))
        .rejects
        .toThrow('Failed to update account');
    });
  });

  describe('editAgnosticBlockchainAccount', () => {
    it('sends PATCH request to chain type endpoint', async () => {
      let capturedBody: Record<string, unknown> | null = null;
      let capturedUrl = '';

      server.use(
        http.patch(`${backendUrl}/api/1/blockchains/type/:chainType/accounts`, async ({ request }) => {
          capturedUrl = request.url;
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { editAgnosticBlockchainAccount } = useBlockchainAccountsApi();
      const result = await editAgnosticBlockchainAccount('evm', {
        address: '0x1234567890123456789012345678901234567890',
        label: 'Agnostic Label',
        tags: ['evm'],
      });

      expect(capturedUrl).toContain('/blockchains/type/evm/accounts');
      expect(capturedBody).toEqual({
        accounts: [
          {
            address: '0x1234567890123456789012345678901234567890',
            label: 'Agnostic Label',
            tags: ['evm'],
          },
        ],
      });
      expect(result).toBe(true);
    });
  });

  describe('editBtcAccount', () => {
    it('sends PATCH request for regular BTC account', async () => {
      let capturedBody: Record<string, unknown> | null = null;
      let capturedUrl = '';

      server.use(
        http.patch(`${backendUrl}/api/1/blockchains/:chain/accounts`, async ({ request }) => {
          capturedUrl = request.url;
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: {
              standalone: [
                {
                  address: 'bc1q...',
                  label: 'BTC Account',
                  tags: ['btc'],
                },
              ],
              xpubs: [],
            },
            message: '',
          });
        }),
      );

      const { editBtcAccount } = useBlockchainAccountsApi();
      const payload: AccountPayload = {
        address: 'bc1q...',
        label: 'BTC Account',
        tags: ['btc'],
      };
      const result = await editBtcAccount(payload, 'btc');

      expect(capturedUrl).toContain('/blockchains/btc/accounts');
      expect(capturedBody).toEqual({
        accounts: [
          {
            address: 'bc1q...',
            label: 'BTC Account',
            tags: ['btc'],
          },
        ],
      });
      expect(result.standalone).toHaveLength(1);
      expect(result.standalone[0].label).toBe('BTC Account');
    });

    it('sends PATCH request for xpub account to xpub endpoint', async () => {
      let capturedBody: Record<string, unknown> | null = null;
      let capturedUrl = '';

      server.use(
        http.patch(`${backendUrl}/api/1/blockchains/:chain/xpub`, async ({ request }) => {
          capturedUrl = request.url;
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: {
              standalone: [],
              xpubs: [
                {
                  xpub: 'xpub6CUGRUo...',
                  derivation_path: 'm/44\'/0\'/0\'',
                  label: 'My Xpub',
                  tags: ['bitcoin'],
                  addresses: null,
                },
              ],
            },
            message: '',
          });
        }),
      );

      const { editBtcAccount } = useBlockchainAccountsApi();
      const payload: XpubAccountPayload = {
        xpub: {
          xpub: 'xpub6CUGRUo...',
          derivationPath: 'm/44\'/0\'/0\'',
          xpubType: XpubKeyType.XPUB,
        },
        label: 'My Xpub',
        tags: ['bitcoin'],
      };
      const result = await editBtcAccount(payload, 'btc');

      expect(capturedUrl).toContain('/blockchains/btc/xpub');
      expect(capturedBody).toEqual({
        xpub: 'xpub6CUGRUo...',
        derivation_path: 'm/44\'/0\'/0\'',
        label: 'My Xpub',
        tags: ['bitcoin'],
      });
      expect(result.xpubs).toHaveLength(1);
    });
  });

  describe('queryAccounts', () => {
    it('fetches accounts for blockchain', async () => {
      let capturedUrl = '';

      server.use(
        http.get(`${backendUrl}/api/1/blockchains/:chain/accounts`, ({ request }) => {
          capturedUrl = request.url;
          return HttpResponse.json({
            result: [
              {
                address: '0x1234567890123456789012345678901234567890',
                label: 'My ETH Account',
                tags: ['main'],
              },
            ],
            message: '',
          });
        }),
      );

      const { queryAccounts } = useBlockchainAccountsApi();
      const result = await queryAccounts('eth');

      expect(capturedUrl).toContain('/blockchains/eth/accounts');
      expect(result).toHaveLength(1);
      expect(result[0].address).toBe('0x1234567890123456789012345678901234567890');
      expect(result[0].label).toBe('My ETH Account');
    });

    it('throws error on failure', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/blockchains/:chain/accounts`, () =>
          HttpResponse.json({
            result: null,
            message: 'Blockchain not supported',
          })),
      );

      const { queryAccounts } = useBlockchainAccountsApi();

      await expect(queryAccounts('unknown'))
        .rejects
        .toThrow('Blockchain not supported');
    });
  });

  describe('queryBtcAccounts', () => {
    it('fetches BTC accounts with standalone and xpubs', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/blockchains/:chain/accounts`, () =>
          HttpResponse.json({
            result: {
              standalone: [
                {
                  address: 'bc1q...',
                  label: 'BTC Standalone',
                  tags: null,
                },
              ],
              xpubs: [
                {
                  xpub: 'xpub6CUGRUo...',
                  derivation_path: 'm/44\'/0\'/0\'',
                  label: 'My Xpub',
                  tags: ['hd'],
                  addresses: [
                    {
                      address: 'bc1qderived...',
                      label: null,
                      tags: null,
                    },
                  ],
                },
              ],
            },
            message: '',
          })),
      );

      const { queryBtcAccounts } = useBlockchainAccountsApi();
      const result = await queryBtcAccounts(Blockchain.BTC);

      expect(result.standalone).toHaveLength(1);
      expect(result.standalone[0].address).toBe('bc1q...');
      expect(result.xpubs).toHaveLength(1);
      expect(result.xpubs[0].xpub).toBe('xpub6CUGRUo...');
      expect(result.xpubs[0].addresses).toHaveLength(1);
    });
  });

  describe('deleteXpub', () => {
    it('sends DELETE request with xpub data in body', async () => {
      let capturedBody: Record<string, unknown> | null = null;
      let capturedUrl = '';

      server.use(
        http.delete(`${backendUrl}/api/1/blockchains/:chain/xpub`, async ({ request }) => {
          capturedUrl = request.url;
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: { task_id: 444 },
            message: '',
          });
        }),
      );

      const { deleteXpub } = useBlockchainAccountsApi();
      const params: DeleteXpubParams = {
        chain: 'btc',
        xpub: 'xpub6CUGRUo...',
        derivationPath: 'm/44\'/0\'/0\'',
      };
      const result = await deleteXpub(params);

      expect(capturedUrl).toContain('/blockchains/btc/xpub');
      expect(capturedBody).toEqual({
        async_query: true,
        xpub: 'xpub6CUGRUo...',
        derivation_path: 'm/44\'/0\'/0\'',
      });
      expect(result.taskId).toBe(444);
    });

    it('handles xpub without derivation path', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.delete(`${backendUrl}/api/1/blockchains/:chain/xpub`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: { task_id: 555 },
            message: '',
          });
        }),
      );

      const { deleteXpub } = useBlockchainAccountsApi();
      await deleteXpub({ chain: 'btc', xpub: 'xpub123' });

      expect(capturedBody).toEqual({
        async_query: true,
        xpub: 'xpub123',
      });
    });

    it('throws error on failure', async () => {
      server.use(
        http.delete(`${backendUrl}/api/1/blockchains/:chain/xpub`, () =>
          HttpResponse.json({
            result: null,
            message: 'Xpub not found',
          })),
      );

      const { deleteXpub } = useBlockchainAccountsApi();

      await expect(deleteXpub({ chain: 'btc', xpub: 'unknown' }))
        .rejects
        .toThrow('Xpub not found');
    });
  });

  describe('getEth2Validators', () => {
    it('fetches validators without payload', async () => {
      let capturedParams: URLSearchParams | null = null;

      server.use(
        http.get(`${backendUrl}/api/1/blockchains/eth2/validators`, ({ request }) => {
          const url = new URL(request.url);
          capturedParams = url.searchParams;
          return HttpResponse.json({
            result: {
              entries: [
                {
                  index: 123456,
                  public_key: '0xabc123...',
                  ownership_percentage: '100',
                  status: 'active',
                },
              ],
              entries_found: 1,
              entries_limit: 50,
            },
            message: '',
          });
        }),
      );

      const { getEth2Validators } = useBlockchainAccountsApi();
      const result = await getEth2Validators();

      expect(capturedParams!.toString()).toBe('');
      expect(result.entries).toHaveLength(1);
      expect(result.entries[0].index).toBe(123456);
    });

    it('fetches validators with filter payload in snake_case', async () => {
      let capturedParams: URLSearchParams | null = null;

      server.use(
        http.get(`${backendUrl}/api/1/blockchains/eth2/validators`, ({ request }) => {
          const url = new URL(request.url);
          capturedParams = url.searchParams;
          return HttpResponse.json({
            result: {
              entries: [],
              entries_found: 0,
              entries_limit: 50,
            },
            message: '',
          });
        }),
      );

      const { getEth2Validators } = useBlockchainAccountsApi();
      const payload: EthValidatorFilter = {
        validatorIndices: [123, 456],
        status: 'active',
      };
      await getEth2Validators(payload);

      expect(capturedParams!.get('validator_indices')).toBe('123,456');
      expect(capturedParams!.get('status')).toBe('active');
    });

    it('throws error on failure', async () => {
      server.use(
        http.get(`${backendUrl}/api/1/blockchains/eth2/validators`, () =>
          HttpResponse.json({
            result: null,
            message: 'ETH2 service unavailable',
          })),
      );

      const { getEth2Validators } = useBlockchainAccountsApi();

      await expect(getEth2Validators())
        .rejects
        .toThrow('ETH2 service unavailable');
    });
  });

  describe('addEth2Validator', () => {
    it('sends PUT request with validator data in snake_case', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.put(`${backendUrl}/api/1/blockchains/eth2/validators`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: { task_id: 666 },
            message: '',
          });
        }),
      );

      const { addEth2Validator } = useBlockchainAccountsApi();
      const payload: Eth2Validator = {
        validatorIndex: '123456',
        publicKey: '0xabc123...',
        ownershipPercentage: '100',
      };
      const result = await addEth2Validator(payload);

      expect(capturedBody).toEqual({
        async_query: true,
        validator_index: '123456',
        public_key: '0xabc123...',
        ownership_percentage: '100',
      });
      expect(result.taskId).toBe(666);
    });

    it('handles validator with only public key', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.put(`${backendUrl}/api/1/blockchains/eth2/validators`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: { task_id: 777 },
            message: '',
          });
        }),
      );

      const { addEth2Validator } = useBlockchainAccountsApi();
      await addEth2Validator({ publicKey: '0xdef456...' });

      expect(capturedBody).toEqual({
        async_query: true,
        public_key: '0xdef456...',
      });
    });

    it('throws error on failure', async () => {
      server.use(
        http.put(`${backendUrl}/api/1/blockchains/eth2/validators`, () =>
          HttpResponse.json({
            result: null,
            message: 'Invalid validator',
          })),
      );

      const { addEth2Validator } = useBlockchainAccountsApi();

      await expect(addEth2Validator({ validatorIndex: 'invalid' }))
        .rejects
        .toThrow('Invalid validator');
    });
  });

  describe('editEth2Validator', () => {
    it('sends PATCH request with validator data in snake_case', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.patch(`${backendUrl}/api/1/blockchains/eth2/validators`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { editEth2Validator } = useBlockchainAccountsApi();
      const result = await editEth2Validator({
        validatorIndex: '123456',
        ownershipPercentage: '50',
      });

      expect(capturedBody).toEqual({
        validator_index: '123456',
        ownership_percentage: '50',
      });
      expect(result).toBe(true);
    });

    it('throws error on failure', async () => {
      server.use(
        http.patch(`${backendUrl}/api/1/blockchains/eth2/validators`, () =>
          HttpResponse.json({
            result: null,
            message: 'Validator not found',
          })),
      );

      const { editEth2Validator } = useBlockchainAccountsApi();

      await expect(editEth2Validator({ validatorIndex: 'unknown' }))
        .rejects
        .toThrow('Validator not found');
    });
  });

  describe('deleteEth2Validators', () => {
    it('sends DELETE request with validator indices in body', async () => {
      let capturedBody: Record<string, unknown> | null = null;

      server.use(
        http.delete(`${backendUrl}/api/1/blockchains/eth2/validators`, async ({ request }) => {
          capturedBody = await request.json() as Record<string, unknown>;
          return HttpResponse.json({
            result: true,
            message: '',
          });
        }),
      );

      const { deleteEth2Validators } = useBlockchainAccountsApi();
      const validators: Eth2ValidatorEntry[] = [
        { index: 123456, publicKey: '0xabc...', ownershipPercentage: '100', status: 'active' },
        { index: 789012, publicKey: '0xdef...', ownershipPercentage: '50', status: 'active' },
      ];
      const result = await deleteEth2Validators(validators);

      expect(capturedBody).toEqual({
        validators: [123456, 789012],
      });
      expect(result).toBe(true);
    });

    it('throws error on failure', async () => {
      server.use(
        http.delete(`${backendUrl}/api/1/blockchains/eth2/validators`, () =>
          HttpResponse.json({
            result: null,
            message: 'Failed to delete validators',
          })),
      );

      const { deleteEth2Validators } = useBlockchainAccountsApi();

      await expect(deleteEth2Validators([{ index: 999, publicKey: '0x...', ownershipPercentage: '100', status: 'active' }]))
        .rejects
        .toThrow('Failed to delete validators');
    });
  });
});
