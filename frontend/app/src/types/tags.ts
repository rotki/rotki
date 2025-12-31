import { z } from 'zod/v4';

export const Tag = z.object({
  backgroundColor: z.string(),
  description: z.string().nullable(),
  foregroundColor: z.string(),
  name: z.string(),
});

export type Tag = z.infer<typeof Tag>;

export const Tags = z.record(z.string(), Tag);

export type Tags = z.infer<typeof Tags>;

export function defaultTag(): Tag {
  return {
    backgroundColor: 'E3E3E3',
    description: null,
    foregroundColor: '000000',
    name: '',
  };
}

// Reserved system tags that cannot be deleted or renamed
export const RESERVED_TAGS: readonly string[] = ['Contract'] as const;

export function isReservedTag(tagName: string): boolean {
  return RESERVED_TAGS.some(reserved =>
    reserved.toLowerCase() === tagName.toLowerCase(),
  );
}
