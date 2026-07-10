import type { WritableComputedRef } from 'vue';
import { type BigNumber, bigNumberify } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { nullDefined, refOptional, useBigNumberModel, useRefPropVModel } from '@/modules/core/common/validation/model';

function writable<T>(initial: T): WritableComputedRef<T> {
  const state = shallowRef<T>(initial);
  return computed<T>({
    get: () => get(state),
    set: (value: T) => set(state, value),
  });
}

describe('model-utils', () => {
  it('should properly map computed property to parent ref', () => {
    const objRef = ref({
      title: 'title',
      value: 'value',
    });

    const prop = useRefPropVModel(objRef, 'value');
    expect(get(objRef).value).toBe('value');
    expect(get(prop)).toBe('value');
    set(prop, 'newValue');
    expect(get(prop)).toBe('newValue');
    expect(get(objRef).value).toBe('newValue');
  });
});

describe('useBigNumberModel', () => {
  it('should render an empty string for a null value', () => {
    const model = useBigNumberModel(writable<BigNumber | null | undefined>(null));
    expect(get(model)).toBe('');
  });

  it('should render an empty string for a NaN value', () => {
    const model = useBigNumberModel(writable<BigNumber | null | undefined>(bigNumberify(Number.NaN)));
    expect(get(model)).toBe('');
  });

  it('should render the string form of a valid number', () => {
    const model = useBigNumberModel(writable<BigNumber | null | undefined>(bigNumberify(42)));
    expect(get(model)).toBe('42');
  });

  it('should parse a string back into a big number', () => {
    const source = writable<BigNumber | null | undefined>(null);
    const model = useBigNumberModel(source);
    set(model, '123');
    expect(get(source)?.toNumber()).toBe(123);
  });

  it('should store null when the string is empty', () => {
    const source = writable<BigNumber | null | undefined>(bigNumberify(1));
    const model = useBigNumberModel(source);
    set(model, '');
    expect(get(source)).toBeNull();
  });
});

describe('nullDefined', () => {
  it('should expose null as undefined', () => {
    const model = nullDefined(writable<number | null>(null));
    expect(get(model)).toBeUndefined();
  });

  it('should store undefined as null', () => {
    const source = writable<number | null>(5);
    const model = nullDefined(source);
    set(model, undefined);
    expect(get(source)).toBeNull();
  });
});

describe('refOptional', () => {
  it('should fall back to the default value when null', () => {
    const model = refOptional(writable<number | null | undefined>(null), 10);
    expect(get(model)).toBe(10);
  });

  it('should store undefined when set to a nullish value', () => {
    const source = writable<number | null | undefined>(3);
    const model = refOptional(source, 10);
    set(model, undefined);
    expect(get(source)).toBeUndefined();
  });
});

describe('useRefPropVModel transform', () => {
  it('should apply the transform when the value is truthy', () => {
    const obj = ref<{ name: string }>({ name: 'alice' });
    const model = useRefPropVModel(obj, 'name', { transform: value => value.toUpperCase() });
    set(model, 'bob');
    expect(get(obj).name).toBe('BOB');
  });

  it('should skip the transform for a falsy value', () => {
    const obj = ref<{ name: string }>({ name: 'alice' });
    const model = useRefPropVModel(obj, 'name', { transform: value => value.toUpperCase() });
    set(model, '');
    expect(get(obj).name).toBe('');
  });
});
