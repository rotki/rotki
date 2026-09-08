import { SUPPORT_EMAIL } from '@shared/external-links';
import { describe, expect, it } from 'vitest';
import {
  encodeIssue,
  githubIssueUrl,
  gmailComposeUrl,
  googleFormUrl,
  isSubmittable,
  MAX_DESCRIPTION_LENGTH,
  MAX_TITLE_LENGTH,
  supportMailtoUrl,
} from '@/modules/shell/components/report-issue-links';

const draft = { description: 'it crashed on save', title: 'Crash on save' };

const googleForm = {
  descriptionEntry: 'entry.2',
  titleEntry: 'entry.1',
  url: 'https://docs.google.com/forms/d/e/abc/viewform',
};

describe('isSubmittable', () => {
  it('should accept a draft with a title', () => {
    expect(isSubmittable(draft)).toBe(true);
  });

  it('should accept a draft with no description', () => {
    expect(isSubmittable({ description: '', title: 'Crash on save' })).toBe(true);
  });

  it('should reject a draft with no title', () => {
    expect(isSubmittable({ description: 'it crashed', title: '' })).toBe(false);
  });

  /** A title of spaces produces an issue with a blank subject, which is as useless as none. */
  it('should reject a title of only whitespace', () => {
    expect(isSubmittable({ description: 'it crashed', title: '   \t ' })).toBe(false);
  });
});

describe('encodeIssue', () => {
  it('should percent encode what the user typed', () => {
    expect(encodeIssue({ description: 'a & b', title: 'a b' })).toEqual({
      description: 'a%20%26%20b',
      title: 'a%20b',
    });
  });

  it('should cut a long title to the limit before encoding', () => {
    const { title } = encodeIssue({ description: '', title: 'a'.repeat(MAX_TITLE_LENGTH + 50) });

    expect(title).toHaveLength(MAX_TITLE_LENGTH);
  });

  it('should cut a long description to the limit before encoding', () => {
    const { description } = encodeIssue({
      description: 'b'.repeat(MAX_DESCRIPTION_LENGTH + 500),
      title: '',
    });

    expect(description).toHaveLength(MAX_DESCRIPTION_LENGTH);
  });

  /**
   * Truncating after encoding could cut a percent escape in half and produce a url the browser
   * rejects, so the cut has to happen first.
   */
  it('should not leave a half written escape when it cuts', () => {
    const { title } = encodeIssue({ description: '', title: `${'a'.repeat(MAX_TITLE_LENGTH - 1)}&&&` });

    expect(title).toBe(`${'a'.repeat(MAX_TITLE_LENGTH - 1)}%26`);
  });

  it('should leave a draft within the limits alone', () => {
    expect(encodeIssue({ description: 'short', title: 'short' })).toEqual({
      description: 'short',
      title: 'short',
    });
  });
});

describe('the submission links', () => {
  it('should pre-fill the github issue form', () => {
    const url = githubIssueUrl(draft);

    expect(url).toContain('title=Crash%20on%20save');
    expect(url).toContain('body=it%20crashed%20on%20save');
  });

  it('should pre-fill the google form through its configured entries', () => {
    const url = googleFormUrl(draft, googleForm);

    expect(url).toBe(`${googleForm.url}?entry.1=Crash%20on%20save&entry.2=it%20crashed%20on%20save`);
  });

  it('should compose a mail to support', () => {
    const url = supportMailtoUrl(draft);

    expect(url).toBe(`mailto:${SUPPORT_EMAIL}?subject=Crash%20on%20save&body=it%20crashed%20on%20save`);
  });

  it('should encode the support address for the gmail link', () => {
    const url = gmailComposeUrl(draft);

    expect(url).toContain(`to=${encodeURIComponent(SUPPORT_EMAIL)}`);
    expect(url).toContain('su=Crash%20on%20save');
  });

  it('should apply the length limits to every destination', () => {
    const long = { description: 'b'.repeat(MAX_DESCRIPTION_LENGTH + 100), title: 'a'.repeat(MAX_TITLE_LENGTH + 100) };

    for (const url of [githubIssueUrl(long), supportMailtoUrl(long), gmailComposeUrl(long), googleFormUrl(long, googleForm)])
      expect(url).not.toContain('a'.repeat(MAX_TITLE_LENGTH + 1));
  });
});
