import { type Tag } from '@/types/user';

export interface TagEvent {
  readonly name?: string;
  readonly description?: string;
  readonly foregroundColor?: string;
  readonly backgroundColor?: string;
}

export const defaultTag = (): Tag => ({
  name: '',
  description: '',
  foregroundColor: '000000',
  backgroundColor: 'E3E3E3'
});
