import type { SetupContext } from 'vue';
import { omit, pick } from 'es-toolkit';

type SetupContextAttrs = SetupContext['attrs'];

type SetupContextAttrsKeys = (keyof SetupContextAttrs)[];

/**
 * The attribute names that belong on the root element: every `data-*` key in the fallthrough attrs.
 */
function getRootKeys(data: SetupContextAttrs): SetupContextAttrsKeys {
  return Object.keys(data).filter(key =>
    key.startsWith('data-'),
  );
}

/**
 * Picks the attributes that belong on a component's root element.
 *
 * @param data - the component's fallthrough attrs
 * @param include - names to keep alongside the `data-*` ones; defaults to `class` alone
 */
export function getRootAttrs(data: SetupContextAttrs, include: SetupContextAttrsKeys = ['class']): Pick<SetupContextAttrs, typeof include[number]> {
  return pick(data, [...getRootKeys(data), ...include]);
}

/**
 * The complement of {@link getRootAttrs}: everything meant for an inner element.
 *
 * @param data - the component's fallthrough attrs
 * @param exclude - names to drop alongside the `data-*` ones; defaults to `class` alone
 */
export function getNonRootAttrs(data: SetupContextAttrs, exclude: SetupContextAttrsKeys = ['class']): Omit<SetupContextAttrs, typeof exclude[number]> {
  return omit(data, [...getRootKeys(data), ...exclude]);
}
