import { describe, expect, it } from 'vitest';
import {
  boolParam,
  enumParam,
  listParam,
  refParams,
  stringParam,
} from '@/modules/core/table/param-refs';

const Handling = {
  EXCLUDE: 'exclude',
  ONLY: 'only',
} as const;

type Handling = typeof Handling[keyof typeof Handling];

function isHandling(value: string): value is Handling {
  return Object.values<string>(Handling).includes(value);
}

describe('stringParam', () => {
  it('should read the first value the query carried', () => {
    const model = ref<string>('');
    stringParam(model).read('kraken');
    expect(get(model)).toBe('kraken');
  });

  it('should clear the ref when the key is absent', () => {
    const model = ref<string>('kraken');
    stringParam(model).read(undefined);
    expect(get(model)).toBe('');
  });

  // The url is the user's to write, so a value the table cannot honour must not reach the request.
  it('should refuse a value it does not admit', () => {
    const model = ref<string>('');
    stringParam(model, { admit: value => value === 'kraken' }).read('nonsense');
    expect(get(model)).toBe('');
  });
});

describe('listParam', () => {
  it('should read a repeated param as a list', () => {
    const model = ref<string[]>([]);
    listParam(model).read(['eth', 'optimism']);
    expect(get(model)).toStrictEqual(['eth', 'optimism']);
  });

  it('should read a single value as a one-item list', () => {
    const model = ref<string[]>([]);
    listParam(model).read('eth');
    expect(get(model)).toStrictEqual(['eth']);
  });

  it('should clear the ref when the key is absent', () => {
    const model = ref<string[]>(['eth']);
    listParam(model).read(undefined);
    expect(get(model)).toStrictEqual([]);
  });

  it('should drop the values it does not admit', () => {
    const model = ref<string[]>([]);
    listParam(model, { admit: value => value === 'eth' }).read(['eth', 'gone']);
    expect(get(model)).toStrictEqual(['eth']);
  });

  it('should split a key the url carries as one joined string', () => {
    const model = ref<string[]>([]);
    listParam(model, { separator: ',' }).read('0xabc,0xdef');
    expect(get(model)).toStrictEqual(['0xabc', '0xdef']);
  });

  // The url half stringifies an array to exactly this, so writing the list back joined would put
  // the joined string in the request payload as well.
  it('should write the list itself even when the url carries it joined', () => {
    const model = ref<string[]>(['0xabc', '0xdef']);
    expect(listParam(model, { separator: ',' }).write()).toStrictEqual(['0xabc', '0xdef']);
  });

  // A trailing separator would otherwise read as an empty id and be sent on as one.
  it('should drop empty entries when splitting', () => {
    const model = ref<string[]>([]);
    listParam(model, { separator: ',' }).read('0xabc,');
    expect(get(model)).toStrictEqual(['0xabc']);
  });
});

describe('boolParam', () => {
  it('should read only the written true as on', () => {
    const model = ref<boolean>(false);
    const param = boolParam(model);

    param.read('true');
    expect(get(model)).toBe(true);

    param.read('false');
    expect(get(model)).toBe(false);

    param.read('true');
    param.read(undefined);
    expect(get(model)).toBe(false);
  });
});

describe('enumParam', () => {
  it('should read a member of the set', () => {
    const model = ref<Handling>(Handling.EXCLUDE);
    enumParam(model, isHandling, Handling.EXCLUDE).read('only');
    expect(get(model)).toBe(Handling.ONLY);
  });

  // Sent on to the backend otherwise, while the pill claimed the default.
  it('should fall back on a value the set does not contain', () => {
    const model = ref<Handling>(Handling.ONLY);
    enumParam(model, isHandling, Handling.EXCLUDE).read('nonsense');
    expect(get(model)).toBe(Handling.EXCLUDE);
  });

  it('should fall back when the key is absent', () => {
    const model = ref<Handling>(Handling.ONLY);
    enumParam(model, isHandling, Handling.EXCLUDE).read(undefined);
    expect(get(model)).toBe(Handling.EXCLUDE);
  });
});

describe('refParams', () => {
  it('should carry the caller\'s destination through', () => {
    const source = refParams({ tags: listParam(ref<string[]>([])) }, { skipEmpty: true, to: 'both' });
    expect(source.to).toBe('both');
    expect(source.skipEmpty).toBe(true);
  });

  it('should build the values off every declared key', () => {
    const tags = ref<string[]>(['a']);
    const strict = ref<boolean>(true);
    const source = refParams({ strictBlockchain: boolParam(strict), tags: listParam(tags) }, { to: 'both' });

    expect(toValue(source.values)).toStrictEqual({ strictBlockchain: true, tags: ['a'] });
  });

  // The whole point: one declaration drives both halves, so they cannot describe different keys.
  it('should round-trip a query back through the same keys', () => {
    const tags = ref<string[]>([]);
    const strict = ref<boolean>(false);
    const source = refParams({ strictBlockchain: boolParam(strict), tags: listParam(tags) }, { to: 'both' });

    source.fromQuery?.({ strictBlockchain: 'true', tags: ['a', 'b'] });

    expect(get(tags)).toStrictEqual(['a', 'b']);
    expect(get(strict)).toBe(true);
    expect(toValue(source.values)).toStrictEqual({ strictBlockchain: true, tags: ['a', 'b'] });
  });

  // The url carries a list joined and the request carries it as a list. Both come off one
  // declaration, so the shape the source emits has to survive the trip through the url form.
  it('should round-trip a list through its joined url form', () => {
    const tags = ref<string[]>(['a', 'b']);
    const source = refParams({ tags: listParam(tags, { separator: ',' }) }, { to: 'both' });

    expect(toValue(source.values)).toStrictEqual({ tags: ['a', 'b'] });

    set(tags, []);
    // What `collectSources` puts in the url for that value: an array stringifies comma-joined.
    source.fromQuery?.({ tags: String(['a', 'b']) });

    expect(get(tags)).toStrictEqual(['a', 'b']);
  });

  // A key the query omits has to be cleared, not left holding what a previous route put there:
  // removing a pill is how a filter is turned off.
  it('should clear a key the query no longer carries', () => {
    const tags = ref<string[]>(['stale']);
    const source = refParams({ tags: listParam(tags) }, { to: 'both' });

    source.fromQuery?.({});

    expect(get(tags)).toStrictEqual([]);
  });
});
