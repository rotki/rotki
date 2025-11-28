import { BigNumber } from '@rotki/common';
import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useTradeApi } from './use-trade-api';

const backendUrl = process.env.VITE_BACKEND_URL;

describe('modules/onchain/send/use-trade-api', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('useTradeApi', () => {
    describe('prepareERC20Transfer', () => {
      it('sends POST request with snake_case payload', async () => {
        let capturedBody: unknown;

        server.use(
          http.post(`${backendUrl}/api/1/wallet/transfer/token`, async ({ request }) => {
            capturedBody = await request.json();
            return HttpResponse.json({
              result: {
                chain_id: 1,
                data: '0x1234567890',
                from: '0xSender',
                nonce: 5,
                to: '0xTokenContract',
                value: 0,
              },
              message: '',
            });
          }),
        );

        const { prepareERC20Transfer } = useTradeApi();
        const result = await prepareERC20Transfer({
          fromAddress: '0xSender',
          toAddress: '0xReceiver',
          amount: '1000000000000000000',
          token: '0xTokenContract',
        });

        expect(capturedBody).toEqual({
          from_address: '0xSender',
          to_address: '0xReceiver',
          amount: '1000000000000000000',
          token: '0xTokenContract',
        });

        expect(result.data).toBe('0x1234567890');
        expect(result.to).toBe('0xTokenContract');
        expect(result.chainId).toBe(1);
        expect(result.from).toBe('0xSender');
        expect(result.nonce).toBe(5);
        expect(result.value).toBe(BigInt(0));
      });
    });

    describe('prepareNativeTransfer', () => {
      it('sends POST request with snake_case payload', async () => {
        let capturedBody: unknown;

        server.use(
          http.post(`${backendUrl}/api/1/wallet/transfer/native`, async ({ request }) => {
            capturedBody = await request.json();
            return HttpResponse.json({
              result: {
                from: '0xSender',
                nonce: 10,
                to: '0xReceiver',
                value: 1000000000000000000,
              },
              message: '',
            });
          }),
        );

        const { prepareNativeTransfer } = useTradeApi();
        const result = await prepareNativeTransfer({
          fromAddress: '0xSender',
          toAddress: '0xReceiver',
          amount: '1000000000000000000',
          chain: 'ethereum',
        });

        expect(capturedBody).toEqual({
          from_address: '0xSender',
          to_address: '0xReceiver',
          amount: '1000000000000000000',
          chain: 'ethereum',
        });

        expect(result.from).toBe('0xSender');
        expect(result.nonce).toBe(10);
        expect(result.to).toBe('0xReceiver');
        expect(result.value).toBe(BigInt(1000000000000000000));
      });
    });

    describe('getIsInteractedBefore', () => {
      it('sends POST request and returns boolean result', async () => {
        let capturedBody: unknown;

        server.use(
          http.post(`${backendUrl}/api/1/wallet/interacted`, async ({ request }) => {
            capturedBody = await request.json();
            return HttpResponse.json({
              result: true,
              message: '',
            });
          }),
        );

        const { getIsInteractedBefore } = useTradeApi();
        const result = await getIsInteractedBefore('0xSender', '0xReceiver');

        expect(capturedBody).toEqual({
          from_address: '0xSender',
          to_address: '0xReceiver',
        });

        expect(result).toBe(true);
      });

      it('returns false when addresses never interacted', async () => {
        server.use(
          http.post(`${backendUrl}/api/1/wallet/interacted`, () =>
            HttpResponse.json({
              result: false,
              message: '',
            })),
        );

        const { getIsInteractedBefore } = useTradeApi();
        const result = await getIsInteractedBefore('0xNew', '0xUnknown');

        expect(result).toBe(false);
      });
    });

    describe('getAssetBalance', () => {
      it('sends POST request and returns BigNumber', async () => {
        let capturedBody: unknown;

        server.use(
          http.post(`${backendUrl}/api/1/wallet/balance`, async ({ request }) => {
            capturedBody = await request.json();
            return HttpResponse.json({
              result: '1500000000000000000',
              message: '',
            });
          }),
        );

        const { getAssetBalance } = useTradeApi();
        const result = await getAssetBalance({
          evmChain: 'ethereum',
          address: '0xWallet',
          asset: 'ETH',
        });

        expect(capturedBody).toEqual({
          evm_chain: 'ethereum',
          address: '0xWallet',
          asset: 'ETH',
        });

        expect(result).toBeInstanceOf(BigNumber);
        expect(result.toString()).toBe('1500000000000000000');
      });

      it('returns Zero when result is null', async () => {
        server.use(
          http.post(`${backendUrl}/api/1/wallet/balance`, () =>
            HttpResponse.json({
              result: null,
              message: '',
            })),
        );

        const { getAssetBalance } = useTradeApi();
        const result = await getAssetBalance({
          evmChain: 'ethereum',
          address: '0xEmpty',
          asset: 'ETH',
        });

        expect(result.isZero()).toBe(true);
      });
    });
  });
});
