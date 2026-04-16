import type { Ref, WritableComputedRef } from 'vue';
import { type BigNumber, bigNumberify } from '@rotki/common';

export function useBigNumberModel(model: WritableComputedRef<BigNumber | null | undefined>): WritableComputedRef<string> {
  return computed<string>({
    get() {
      const modelVal = get(model);
      if (!modelVal || modelVal.isNaN())
        return '';
      return modelVal.toString();
    },
    set(value: string) {
      set(model, value ? bigNumberify(value) : null);
    },
  });
}

export function nullDefined<T>(comp: WritableComputedRef<T | null>): WritableComputedRef<T | undefined> {
  return computed<T | undefined>({
    get() {
      return get(comp) ?? undefined;
    },
    set(value?: T | undefined) {
      set(comp, value ?? null);
    },
  });
}

export function refOptional<T>(comp: WritableComputedRef<T | undefined | null>, defaultValue: T): WritableComputedRef<T> {
  return computed<T>({
    get() {
      return get(comp) ?? defaultValue;
    },
    set(value?: T) {
      set(comp, value ?? undefined);
    },
  });
}

export function useRefPropVModel<
  P extends object,
  K extends keyof P,
>(obj: Ref<P>, key: K, options: {
  transform?: (value: NonNullable<P[K]>) => NonNullable<P[K]>;
} = {}): WritableComputedRef<P[K]> {
  const {
    transform = (value: P[K]): P[K] => value,
  } = options;
  return computed<P[K]>({
    get() {
      return get(obj)[key];
    },
    set(value?: P[K]) {
      set(obj, {
        ...get(obj),
        [key]: value ? transform(value) : value,
      });
    },
  });
}
