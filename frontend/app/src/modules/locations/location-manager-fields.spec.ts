import { describe, expect, it } from 'vitest';
import { toLocationTreeFields } from '@/modules/locations/location-manager-fields';

describe('toLocationTreeFields', () => {
  it('should key the tree name filter apart from the name filters of the asset tables', () => {
    const [name] = toLocationTreeFields(key => key);
    expect(name?.key).toBe('locationName');
    expect(name?.freeText).toBe(true);
  });
});
