import type { Ref, WritableComputedRef } from 'vue';

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
