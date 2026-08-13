import { z, type ZodType } from 'zod';
import { requiredField } from '@/modules/core/form/fields';

export interface UserNoteMessages {
  content: string;
}

/**
 * Only the content is required. The title is optional and may be absent altogether, and the rest of
 * the note is carried through the form untouched.
 */
export function userNoteSchema(messages: UserNoteMessages): ZodType {
  return z.object({
    content: requiredField(messages.content),
    title: z.string().optional(),
  });
}
