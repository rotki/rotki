import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { createCustomPinia } from '@test/utils/create-pinia';
import { withSetup } from '@test/utils/with-setup';
import { describe, expect, it } from 'vitest';
import { useEthStakingFilterFields } from './use-eth-staking-filter-fields';
import '@test/i18n';

function fieldsFor(disableStatus: boolean): FieldDef[] {
  setActivePinia(createCustomPinia());
  const { result, wrapper } = withSetup(() => useEthStakingFilterFields(disableStatus));
  const fields = get(result);
  wrapper.unmount();
  return fields;
}

describe('useEthStakingFilterFields', () => {
  it('should collapse the two date bounds into one period field', () => {
    const period = fieldsFor(false).find(field => field.key === 'period');

    expect(period).toMatchObject({
      bounds: { lower: 'fromTimestamp', upper: 'toTimestamp' },
      valueType: 'date',
    });
  });

  it('should offer every status except all', () => {
    const status = fieldsFor(false).find(field => field.key === 'status');

    // `all` is the absence of the pill, so offering it would be a second way to say the same thing.
    expect(status?.suggest?.()).toStrictEqual(['exited', 'active', 'consolidated']);
    expect(status?.multiple).toBe(false);
  });

  it('should read a status as a word rather than its raw value', () => {
    const status = fieldsFor(false).find(field => field.key === 'status');

    expect(status?.resolveLabel?.('consolidated')).toBe('Consolidated');
  });

  // The caller computes this when validators are picked by hand: naming exact validators already
  // decides which ones you get, so a status filter has nothing left to narrow.
  it('should not offer status while validators are picked', () => {
    expect(fieldsFor(true).map(field => field.key)).toStrictEqual(['period']);
  });
});
