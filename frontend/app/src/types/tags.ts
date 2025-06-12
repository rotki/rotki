import { z } from 'zod';

export const Tag = z.object({
  backgroundColor: z.string(),
  description: z.string().nullable(),
  foregroundColor: z.string(),
  name: z.string(),
});

export type Tag = z.infer<typeof Tag>;

export const Tags = z.record(Tag);

export type Tags = z.infer<typeof Tags>;

export function defaultTag(): Tag {
  return {
    backgroundColor: 'E3E3E3',
    description: null,
    foregroundColor: '000000',
    name: '',
  };
}
