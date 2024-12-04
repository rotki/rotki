import { z } from 'zod';

export interface TagEvent {
  readonly name?: string;
  readonly description?: string;
  readonly foregroundColor?: string;
  readonly backgroundColor?: string;
}

export const Tag = z.object({
  name: z.string(),
  description: z.string(),
  backgroundColor: z.string(),
  foregroundColor: z.string(),
});

export type Tag = z.infer<typeof Tag>;

export const Tags = z.record(Tag);

export type Tags = z.infer<typeof Tags>;

export function defaultTag(): Tag {
  return {
    name: '',
    description: '',
    foregroundColor: '000000',
    backgroundColor: 'E3E3E3',
  };
}
