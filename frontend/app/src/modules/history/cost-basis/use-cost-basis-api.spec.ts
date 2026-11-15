import { server } from '@test/setup-files/server';
import { type DefaultBodyType, http, HttpResponse } from 'msw';
import { assert, describe, expect, it } from 'vitest';
import { CostBasisDirection } from '@/modules/history/cost-basis/types';
import { useCostBasisApi } from '@/modules/history/cost-basis/use-cost-basis-api';

const backendUrl = process.env.VITE_BACKEND_URL;

const bucket = { asset: 'ETH', location: 'ethereum', location_label: '0xA', method: 'fifo', protocol: null };

describe('useCostBasisApi', () => {
  it('should send the event identifiers and parse both directions with decimal amounts', async () => {
    let capturedBody: DefaultBodyType = null;
    server.use(http.post(`${backendUrl}/api/1/history/events/cost_basis`, async ({ request }) => {
      capturedBody = await request.json();
      return HttpResponse.json({ message: '', result: {
        entries: {
          12: [{ ...bucket, basis_per_unit: '1000.1234567890123456789', basis_source: 'price_oracle', direction: 'receive', lot_ids: ['12'] }],
          57: [{
            ...bucket,
            basis_removed: '500',
            basis_remaining: '500',
            direction: 'spend',
            lots: [{
              acquired_at: 1675209600,
              acquisition: { group_identifier: '0xgroup', identifier: 12, location: 'ethereum', location_label: '0xA', timestamp: 1675209600000 },
              amount: '0.5',
              basis_per_unit: '1000',
              lot_id: '12',
              taxable: false,
            }, { acquired_at: 5, acquisition: null, amount: '1', basis_per_unit: '0', lot_id: '99', taxable: true }],
            proceeds: null,
            realized_pnl: '400',
            taxfree_pnl: null,
          }],
        },
        method: 'fifo',
        stale: true,
      } });
    }));

    const result = await useCostBasisApi().fetchEventsCostBasis([12, 57]);

    expect(capturedBody).toEqual({ event_identifiers: [12, 57] });
    expect(result.stale).toBe(true);
    expect(result.method).toBe('fifo');

    const [receive] = result.entries['12'];
    assert(receive.direction === CostBasisDirection.RECEIVE);
    expect(receive.basisPerUnit.toString()).toBe('1000.1234567890123456789');
    expect(receive.lotIds).toEqual(['12']);
    expect(receive.locationLabel).toBe('0xA');

    const [spend] = result.entries['57'];
    assert(spend.direction === CostBasisDirection.SPEND);
    expect(spend.proceeds).toBeNull();
    expect(spend.taxfreePnl).toBeNull();
    expect(spend.realizedPnl.toString()).toBe('400');
    expect(spend.lots[0].acquisition).toEqual({ groupIdentifier: '0xgroup', identifier: 12, location: 'ethereum', locationLabel: '0xA', timestamp: 1675209600000 });
    expect(spend.lots[0].taxable).toBe(false);
    expect(spend.lots[1].acquisition).toBeNull();
  });
});
