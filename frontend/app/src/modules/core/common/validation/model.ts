import type { Ref, WritableComputedRef } from 'vue';

/**
 * One field of an object the parent owns, as a writable computed.
 *
 * For a component that holds a payload it does not own and has no form of its own: an account's
 * chain, an accounting rule's value, a set of table toggles. A component that does have a form
 * binds `form.state` directly instead, and one whose inputs cannot hold the payload as it stands
 * maps it once with `useMappedModelForm` rather than wrapping each field here.
 */
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
