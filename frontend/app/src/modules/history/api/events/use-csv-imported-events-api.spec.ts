import { server } from '@test/setup-files/server';
import { type DefaultBodyType, http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';
import { useCsvImportedEventsApi } from '@/modules/history/api/events/use-csv-imported-events-api';

const backendUrl = process.env.VITE_BACKEND_URL;

describe('csv imported events API', () => {
  it('should fetch the import summary', async () => {
    server.use(
      http.get(`${backendUrl}/api/1/history/events/imported`, () => HttpResponse.json({
        result: [{
          customized_events_count: 2,
          events_count: 3,
          location: 'binance',
        }],
        message: '',
      })),
    );

    await expect(useCsvImportedEventsApi().fetchCsvImportedEventsSummary()).resolves.toEqual([{
      customizedEventsCount: 2,
      eventsCount: 3,
      location: 'binance',
    }]);
  });

  it('should delete imports from the selected location', async () => {
    let capturedBody: DefaultBodyType = null;
    server.use(
      http.delete(`${backendUrl}/api/1/history/events/imported`, async ({ request }) => {
        capturedBody = await request.json();
        return HttpResponse.json({ result: true, message: '' });
      }),
    );

    await useCsvImportedEventsApi().deleteCsvImportedEvents('kraken');

    expect(capturedBody).toEqual({ location: 'kraken' });
  });
});
