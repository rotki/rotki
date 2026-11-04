import type { ComputedRef, MaybeRefOrGetter } from 'vue';

export interface SettingOption<TOption> {
  /** The value stored in the setting. */
  value: string;
  label: string;
  /** The option as the caller passed it, for bespoke item rendering. */
  raw: TOption;
}

interface UseSettingOptionsArgs<TOption> {
  options: MaybeRefOrGetter<readonly TOption[]>;
  /** For object options, the property projected as the stored value. Omit for primitive options. */
  keyAttr?: MaybeRefOrGetter<string | undefined>;
  /** For object options, the property shown as the label. Omit for primitive options. */
  textAttr?: MaybeRefOrGetter<string | undefined>;
}

function project(option: unknown, attr: string | undefined): string {
  return attr ? String(Reflect.get(new Object(option), attr)) : String(option);
}

/** Normalises the primitive or object options of a select setting to `{ value, label, raw }`. */
export function useSettingOptions<TOption>(args: UseSettingOptionsArgs<TOption>): ComputedRef<SettingOption<TOption>[]> {
  return computed<SettingOption<TOption>[]>(() => {
    const keyAttr = toValue(args.keyAttr);
    const textAttr = toValue(args.textAttr);
    return toValue(args.options).map(option => ({
      label: project(option, textAttr),
      raw: option,
      value: project(option, keyAttr),
    }));
  });
}
