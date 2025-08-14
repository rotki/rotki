import { beforeEach, describe, expect, it } from 'vitest';
import { useLoggedUserIdentifier } from '@/composables/user/use-logged-user-identifier';
import { useDatabase } from '@/modules/data/use-database';
import {
  type AddMissingMapping,
  type MissingMappingsRequestPayload,
  useMissingMappingsDB,
} from './use-missing-mappings-db';

beforeEach(async () => {
  const user = useLoggedUserIdentifier();
  set(user, 'test-user');
  const { db } = useDatabase();
  await db.missingMappings.clear();
});

function createMissingMapping(data: Pick<AddMissingMapping, 'location' | 'identifier'>): AddMissingMapping {
  return {
    details: 'test',
    name: data.location ? `${data.location} 1` : 'test',
    ...data,
  };
}

function getAssets(length = 10): string[] {
  const digits = length.toString().length;
  return Array.from({ length }, (_, i) => {
    const number = (i + 1).toString().padStart(digits, '0');
    return `ID_${number}`;
  });
}

describe('useMissingMappingsDB', () => {
  it('should insert a new mapping into the database', async () => {
    const { put } = useMissingMappingsDB();
    const { db } = useDatabase();
    const mapping: AddMissingMapping = createMissingMapping({ identifier: 'XYZ', location: 'kraken' });

    const id = await put(mapping);

    const savedMapping = await db.missingMappings.get(id);

    expect(savedMapping).toMatchObject(expect.objectContaining({
      id,
      identifier: 'XYZ',
      location: 'kraken',
    }));
  });

  it('should count the records in the database', async () => {
    const { count, put } = useMissingMappingsDB();
    await put(createMissingMapping({ identifier: 'XYZ', location: 'kraken' }));
    await put(createMissingMapping({ identifier: 'ABC', location: 'binance' }));

    const totalCount = await count();

    expect(totalCount).toBe(2);
  });

  it('should return data correctly', async () => {
    const { getData, put } = useMissingMappingsDB();

    await put(createMissingMapping({ identifier: 'id1', location: 'location1' }));
    await put(createMissingMapping({ identifier: 'id2', location: 'location2' }));
    await put(createMissingMapping({ identifier: 'id3', location: 'location3' }));

    const requestPayload: MissingMappingsRequestPayload = {
      limit: 2,
      offset: 0,
      orderByAttributes: ['location'],
    };

    const { data, found, total } = await getData(requestPayload);

    expect(data.length).toBe(2);
    expect(found).toBe(3);
    expect(total).toBe(3);
    expect(data[0].location).toBe('location1');
    expect(data[1].location).toBe('location2');
  });

  it.each([
    { expected: 'location3', order: 'asc' },
    { expected: 'location1', order: 'desc' },
  ])(`should paginate correctly with $order`, async ({ expected, order }) => {
    const { getData, put } = useMissingMappingsDB();

    const locations = ['location1', 'location2', 'location3'];
    const assets = getAssets();

    for (const location of locations) {
      for (const asset of assets) {
        const mapping = createMissingMapping({ identifier: asset, location });
        await put(mapping);
      }
    }

    const requestPayload: MissingMappingsRequestPayload = {
      ascending: [order === 'asc'],
      limit: 10,
      offset: 20,
      orderByAttributes: ['location'],
    };

    const { data, found, total } = await getData(requestPayload);
    expect(data.length).toBe(10);
    expect(found).toBe(30);
    expect(total).toBe(30);

    for (const datum of data) {
      expect(datum.location).toBe(expected);
    }
  });

  it.each([
    { order: 'asc' },
    { order: 'desc' },
  ])(`should filter based on user input $order`, async ({ order }) => {
    const { getData, put } = useMissingMappingsDB();

    const locations = ['location1', 'location2', 'location3'];
    const assets = getAssets(20);

    for (const location of locations) {
      for (const asset of assets) {
        const mapping = createMissingMapping({ identifier: asset, location });
        await put(mapping);
      }
    }

    const offsets = [0, 10];

    for (const offset of offsets) {
      const requestPayload: MissingMappingsRequestPayload = {
        ascending: [order === 'asc'],
        limit: 10,
        location: 'location2',
        offset,
        orderByAttributes: ['identifier'],
      };

      const { data, found, total } = await getData(requestPayload);

      expect(data.length).toBe(10);
      expect(found).toBe(20);
      expect(total).toBe(20);

      for (const datum of data) {
        expect(datum.location).toBe('location2');
      }

      const sortedAssets = order === 'desc' ? [...assets].reverse() : assets;

      expect(data.map(m => m.identifier), `on order ${order}`).toEqual(sortedAssets.slice(offset, 10 + offset));
    }

    const requestPayload: MissingMappingsRequestPayload = {
      ascending: [order === 'asc'],
      identifier: 'ID_10',
      limit: 10,
      offset: 0,
      orderByAttributes: ['location'],
    };

    const { data, found, total } = await getData(requestPayload);

    expect(data.length).toBe(3);
    expect(found).toBe(3);
    expect(total).toBe(3);
    expect(data.map(m => m.location)).toEqual(order === 'desc' ? [...locations].reverse() : locations);
  });

  it('should remove an asset matched by identifier and location', async () => {
    const { count, put, remove } = useMissingMappingsDB();
    const assetData = { identifier: 'XYZ', location: 'kraken' };
    const mapping: AddMissingMapping = createMissingMapping(assetData);

    await put(mapping);
    expect(await count()).toBe(1);

    await remove(assetData);
    expect(await count()).toBe(0);
  });
});
