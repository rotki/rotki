import { describe, expect, it, vi } from 'vitest';
import { decimalsTextModel, parseDecimals, startedEpochModel } from '@/modules/assets/admin/asset-field-models';

describe('parseDecimals', () => {
  it.each([
    ['18', 18],
    ['0', 0],
    ['6.7', 6],
  ])('should read %s as %s', (typed, expected) => {
    expect(parseDecimals(typed)).toBe(expected);
  });

  it.each([
    [''],
    [undefined],
    ['abc'],
  ])('should read %s as no decimals at all', (typed) => {
    expect(parseDecimals(typed)).toBeNull();
  });
});

describe('decimalsTextModel', () => {
  it('should show the decimals the asset has', () => {
    const decimals = ref<number | null>(18);

    expect(get(decimalsTextModel(decimals))).toBe('18');
  });

  // A new managed asset opens with null decimals. Interpolating that straight into a string is what
  // put the word "null" in the box.
  it.each([
    [null],
    [undefined],
  ])('should show %s as an empty field', (value) => {
    const decimals = ref<number | null | undefined>(value);

    expect(get(decimalsTextModel(decimals))).toBe('');
  });

  it('should tell the caller the field changed', () => {
    const decimals = ref<number | null>(null);
    const changed = vi.fn<() => void>();

    set(decimalsTextModel(decimals, changed), '8');

    expect(changed).toHaveBeenCalledOnce();
  });

  it('should write what was typed back as a number', () => {
    const decimals = ref<number | null>(null);
    const model = decimalsTextModel(decimals);

    set(model, '8');

    expect(get(decimals)).toBe(8);
  });

  it('should clear the decimals when the field is emptied', () => {
    const decimals = ref<number | null>(18);
    const model = decimalsTextModel(decimals);

    set(model, '');

    expect(get(decimals)).toBeNull();
  });
});

describe('startedEpochModel', () => {
  it('should open an asset with no start date at the epoch', () => {
    const started = ref<number | undefined>();

    expect(get(startedEpochModel(started))).toBe(0);
  });

  it('should show the date the asset has', () => {
    const started = ref<number | undefined>(1600000000);

    expect(get(startedEpochModel(started))).toBe(1600000000);
  });

  it('should put the epoch back when the picker is cleared', () => {
    const started = ref<number | undefined>(1600000000);
    const model = startedEpochModel(started);

    set(model, undefined);

    expect(get(started)).toBe(0);
  });
});
