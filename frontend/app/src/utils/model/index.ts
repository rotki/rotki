import { kebabCase } from 'lodash-es';

export function usePropVModel<
  P extends object,
  K extends keyof P,
  S extends P[K] extends object ? keyof P[K] : never,
  Name extends string,
>(props: P, key: K, subKey: S, emit?: (name: Name, ...args: any[]) => void): WritableComputedRef<P[K][S]> {
  const eventName = (key === 'value' ? 'input' : `update:${kebabCase(key.toString())}`) as Name;
  return computed({
    get() {
      return props[key][subKey];
    },
    set(value: P[K][S]) {
      emit?.(eventName, { ...props[key], [subKey]: value });
    },
  });
}

export function useSimplePropVModel<
  T,
  P extends { modelValue: T },
  S extends P['modelValue'] extends object ? keyof P['modelValue'] : never,
  Name extends string,
>(props: P, subKey: S, emit?: (name: Name, ...args: any[]) => void): WritableComputedRef<P['modelValue'][S]> {
  return usePropVModel(props, 'modelValue', subKey, emit);
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

export function refOptional<T>(comp: WritableComputedRef<T | undefined>, defaultValue: T): WritableComputedRef<T> {
  return computed<T>({
    get() {
      return get(comp) ?? defaultValue;
    },
    set(value?: T) {
      set(comp, value ?? undefined);
    },
  });
}

export function useSimpleVModel<T, P extends { modelValue: T }, Name extends string>(
  props: P,
  emit?: (name: Name, ...args: any[]) => void,
): WritableComputedRef<P['modelValue']> {
  return useVModel(props, 'modelValue', emit, {
    eventName: 'update:model-value',
  });
}

export function useRefPropVModel<P extends object, K extends keyof P>(obj: Ref<P>, key: K): WritableComputedRef<P[K]> {
  return computed<P[K]>({
    get() {
      return get(obj)[key];
    },
    set(value?: P[K]) {
      set(obj, {
        ...get(obj),
        [key]: value,
      });
    },
  });
}
