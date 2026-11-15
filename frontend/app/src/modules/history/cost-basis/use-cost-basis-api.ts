import { api } from '@/modules/core/api/rotki-api';
import { EventsCostBasisResponse } from '@/modules/history/cost-basis/types';

interface UseCostBasisApiReturn {
  fetchEventsCostBasis: (eventIdentifiers: number[]) => Promise<EventsCostBasisResponse>;
}

export function useCostBasisApi(): UseCostBasisApiReturn {
  /**
   * The cost basis materialized for each of the given events.
   *
   * @param eventIdentifiers - between 1 and 500 identifiers, the backend rejects more
   */
  async function fetchEventsCostBasis(eventIdentifiers: number[]): Promise<EventsCostBasisResponse> {
    return EventsCostBasisResponse.parse(await api.post('/history/events/cost_basis', { eventIdentifiers }));
  }

  return { fetchEventsCostBasis };
}
