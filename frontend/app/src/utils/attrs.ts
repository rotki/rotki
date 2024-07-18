import { objectOmit, objectPick } from '@vueuse/shared';
import type { SetupContext } from 'vue';

type SetupContextAttrs = SetupContext['attrs'];

type SetupContextAttrsKeys = (keyof SetupContextAttrs)[];

/**
 * Generates and returns the array of root allowed attributes
 * @param {SetupContextAttrs} data
 * @returns {SetupContextAttrsKeys}
 */
export function getRootKeys(data: SetupContextAttrs) {
  return Object.keys(data).filter(key =>
    key.startsWith('data-'),
  ) as SetupContextAttrsKeys;
}

/**
 * Picks only required attributes for root element
 * @param {SetupContextAttrs} data
 * @param {SetupContextAttrsKeys} include
 * @returns {Pick<SetupContextAttrs, any>}
 */
export function getRootAttrs(data: SetupContextAttrs, include: SetupContextAttrsKeys = ['class']) {
  return objectPick(data, [...getRootKeys(data), ...include]);
}

/**
 * Omits root attributes from component's attributes
 * @param {SetupContextAttrs} data
 * @param {SetupContextAttrsKeys} exclude
 * @returns {Omit<SetupContextAttrs, any>}
 */
export function getNonRootAttrs(data: SetupContextAttrs, exclude: SetupContextAttrsKeys = ['class']) {
  return objectOmit(data, [...getRootKeys(data), ...exclude]);
}
