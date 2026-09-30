/**
 * A notification message that says how many times it happened, when that is more than once.
 *
 * @remarks
 * `count` is how many times the message was sent, or how many sends a grouped row now stands for.
 */
export function withRepeats(t: ReturnType<typeof useI18n>['t'], message: string, count: number): string {
  return count > 1 ? t('notification_messages.repeated', { count, message }) : message;
}
