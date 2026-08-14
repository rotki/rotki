import { z, type ZodType } from 'zod';
import { requiredField } from '@/modules/core/form/fields';

export interface CustomAssetMessages {
  customAssetType: string;
  name: string;
}

/**
 * The name and the type are the only rules this form has ever had.
 *
 * Notes carried a rule that always returned true, which existed to hold server errors rather than
 * to reject anything, and the identifier is carried untouched. Both pass through: a structural rule
 * over a field with no message bound to it would block the save with nothing on screen to explain
 * it. Server-side failures arrive through `setServerErrors` instead.
 */
export function customAssetSchema(messages: CustomAssetMessages): ZodType {
  return z.object({
    customAssetType: requiredField(messages.customAssetType),
    name: requiredField(messages.name),
  }).passthrough();
}
