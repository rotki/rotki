import { server } from '@test/setup-files/server';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';
import { useAssetSpamPredictionApi } from './use-asset-spam-prediction-api';

const backendUrl = process.env.VITE_BACKEND_URL;
const colibriUrl = `${backendUrl}/colibri`;

describe('useAssetSpamPredictionApi', () => {
  it('should send the page batch to colibri and parse predictions keyed by the exact identifier', async () => {
    let capturedBody: unknown;

    server.use(
      http.post(`${colibriUrl}/assets/spam/predict`, async ({ request }) => {
        capturedBody = await request.json();
        return HttpResponse.json({
          message: '',
          result: {
            'eip155:1/erc20:0xToken_With_Underscore': {
              flagged: true,
              model_reasons: [{
                feature: 'log_transfer_count',
                probability_delta: 0.12,
                value: 4,
              }],
              observed_signals: ['unverified_contract'],
              spam_probability: 0.87,
              threshold: 0.5,
            },
            'eip155:1/erc20:0xUnknown': null,
          },
        });
      }),
    );

    const { predictSpam } = useAssetSpamPredictionApi();
    const result = await predictSpam([
      { identifier: 'eip155:1/erc20:0xToken_With_Underscore', txReference: '0xabc' },
      { identifier: 'eip155:1/erc20:0xUnknown' },
    ]);

    expect(capturedBody).toEqual({
      tokens: [
        { identifier: 'eip155:1/erc20:0xToken_With_Underscore', tx_reference: '0xabc' },
        { identifier: 'eip155:1/erc20:0xUnknown' },
      ],
    });
    expect(result['eip155:1/erc20:0xToken_With_Underscore']).toEqual({
      flagged: true,
      modelReasons: [{
        feature: 'log_transfer_count',
        probabilityDelta: 0.12,
        value: 4,
      }],
      observedSignals: ['unverified_contract'],
      spamProbability: 0.87,
      threshold: 0.5,
    });
    expect(result['eip155:1/erc20:0xUnknown']).toBeNull();
  });

  it('should report a backend failure instead of silently dropping the rows', async () => {
    server.use(
      http.post(`${colibriUrl}/assets/spam/predict`, () =>
        HttpResponse.json({
          message: 'Batch too large',
          result: null,
        })),
    );

    const { predictSpam } = useAssetSpamPredictionApi();

    await expect(predictSpam([{ identifier: 'eip155:1/erc20:0xToken' }]))
      .rejects
      .toThrow('Batch too large');
  });
});
