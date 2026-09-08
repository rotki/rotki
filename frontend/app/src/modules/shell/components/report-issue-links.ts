import { externalLinks, SUPPORT_EMAIL } from '@shared/external-links';

/**
 * The caps the destinations impose. A github url and a mailto both go through the address bar, so
 * an unbounded description produces a link the browser silently truncates or refuses.
 */
export const MAX_TITLE_LENGTH = 100;

export const MAX_DESCRIPTION_LENGTH = 1500;

/** What the user typed, before it is trimmed to fit a url. */
export interface IssueDraft {
  readonly title: string;
  readonly description: string;
}

/** The same draft, cut to length and percent encoded. */
interface EncodedIssue {
  readonly title: string;
  readonly description: string;
}

/** Where the google form expects the two answers, which the deployment configures. */
export interface GoogleFormConfig {
  readonly url: string;
  readonly titleEntry: string;
  readonly descriptionEntry: string;
}

/**
 * Cuts a draft to what a url can carry and encodes it.
 *
 * @param draft - what the user typed
 * @returns the title and description, truncated then percent encoded
 */
export function encodeIssue(draft: IssueDraft): EncodedIssue {
  return {
    description: encodeURIComponent(draft.description.slice(0, MAX_DESCRIPTION_LENGTH)),
    title: encodeURIComponent(draft.title.slice(0, MAX_TITLE_LENGTH)),
  };
}

/**
 * Whether the draft can be submitted, which asks only for a title.
 *
 * @remarks
 * Whitespace does not count, so a title of spaces is as empty as no title at all. The description
 * is optional, since a reproducible one-line report is worth more than a padded one.
 *
 * @param draft - what the user typed
 * @returns whether any destination will accept it
 */
export function isSubmittable(draft: IssueDraft): boolean {
  return draft.title.trim().length > 0;
}

/** The github issue form, pre-filled. */
export function githubIssueUrl(draft: IssueDraft): string {
  const { description, title } = encodeIssue(draft);
  return `${externalLinks.githubNewBugReport}&title=${title}&body=${description}`;
}

/** The google form, pre-filled through the entry ids the deployment configures. */
export function googleFormUrl(draft: IssueDraft, config: GoogleFormConfig): string {
  const { description, title } = encodeIssue(draft);
  return `${config.url}?${config.titleEntry}=${title}&${config.descriptionEntry}=${description}`;
}

/** A mail client, composing to support. */
export function supportMailtoUrl(draft: IssueDraft): string {
  const { description, title } = encodeIssue(draft);
  return `mailto:${SUPPORT_EMAIL}?subject=${title}&body=${description}`;
}

/** Gmail's compose window, for a user with no mail client registered. */
export function gmailComposeUrl(draft: IssueDraft): string {
  const { description, title } = encodeIssue(draft);
  return `${externalLinks.gmailCompose}&to=${encodeURIComponent(SUPPORT_EMAIL)}&su=${title}&body=${description}`;
}
