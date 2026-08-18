import type { WritableComputedRef } from 'vue';
import { describe, expect, it } from 'vitest';
import { refOptional, useRefPropVModel } from '@/modules/core/common/validation/model';

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
