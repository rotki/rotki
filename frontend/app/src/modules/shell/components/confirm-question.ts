/**
 * What an inline confirmation asks before an action runs, wherever it is asked: beside a button, in
 * place of one, or inside the menu the action sits in.
 */
export interface ConfirmQuestion {
  readonly title?: string;
  /** A line break starts a second paragraph where the question has room for one. */
  readonly message: string;
  /** The accept button's label, naming the action itself ("Delete", "Purge data"). */
  readonly confirmLabel: string;
  /** `error` for an action that destroys data; `warning` otherwise, which is the default. */
  readonly tone?: 'warning' | 'error';
}
