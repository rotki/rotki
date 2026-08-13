import { z, type ZodType } from 'zod';
import { requiredField } from '@/modules/core/form/fields';

export interface TagMessages {
  name: string;
}

/**
 * Only the name is required. The description is nullable on the backend, and the colours are always
 * set, either from the seed or from the shuffle.
 */
export function tagSchema(messages: TagMessages): ZodType {
  return z.object({
    backgroundColor: z.string(),
    description: z.string().nullish(),
    foregroundColor: z.string(),
    name: requiredField(messages.name),
  });
}
