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
  readOnly: z.boolean().default(false).optional(),
  icon: z.string().default('').optional()
});
export type Tag = z.infer<typeof Tag>;

export enum ReadOnlyTag {
  LOOPRING = 'Loopring'
}

export const READ_ONLY_TAGS: Record<ReadOnlyTag, Tag> = {
  [ReadOnlyTag.LOOPRING]: {
    name: ReadOnlyTag.LOOPRING,
    description: ReadOnlyTag.LOOPRING,
    backgroundColor: 'C5DEF5',
    foregroundColor: '000000',
    readOnly: true,
    icon: './assets/images/modules/loopring.svg'
  }
};
export const Tags = z.record(Tag);
export type Tags = z.infer<typeof Tags>;
export const defaultTag = (): Tag => ({
  name: '',
  description: '',
  foregroundColor: '000000',
  backgroundColor: 'E3E3E3'
});
