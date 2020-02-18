export interface TagEvent {
  readonly name?: string;
  readonly description?: string;
  readonly foreground_color?: string;
  readonly background_color?: string;
}

export const defaultTag = () => ({
  name: '',
  description: '',
  foreground_color: '000000',
  background_color: 'E3E3E3'
});
