import { describe, expect, it } from 'vitest';
import { explorerUrlSchema } from '@/modules/settings/explorers/explorer-url-schema';

const schema = explorerUrlSchema({ https: 'not https', url: 'not a url' });

function messagesFor(url: string): string[] {
  const result = schema.safeParse({ url });
  return result.success ? [] : result.error.issues.map(issue => issue.message);
}

describe('settings/explorers/explorer-url-schema', () => {
  it.each([
    ['https://example.com/address/', []],
    ['https://example.com', []],
    ['https://example.com/address/{address}', []],
    ['http://example.com/address/', ['not https']],
    ['https://', ['not a url']],
    ['https:// example.com', ['not a url']],
    ['https://exa mple.com', ['not a url']],
    ['httpsfoo', ['not a url']],
    ['not a url', ['not https', 'not a url']],
  ])('should report %o as %o', (url, expected) => {
    expect(messagesFor(url)).toEqual(expected);
  });

  it('should accept an empty url, which is how an override is cleared', () => {
    expect(messagesFor('')).toEqual([]);
  });
});
