import type { Tag } from '@/modules/tags/tags';
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

/**
 * The tag with its colours in the case the colour pickers write them.
 *
 * @remarks
 * A picker rewrites the hex it is given in lower case as soon as it mounts. Opening the form on
 * `E3E3E3` would therefore read as an edit nobody made, and Cancel would ask to discard it.
 */
export function withPickerColors(tag: Tag): Tag {
  return {
    ...tag,
    backgroundColor: tag.backgroundColor.toLowerCase(),
    foregroundColor: tag.foregroundColor.toLowerCase(),
  };
}
