import { describe, expect, it } from 'vitest';
import {
  hasWhitelistChanges,
  mergeWhitelist,
  parseWhitelistInput,
} from '@/modules/settings/general/nft/nft-whitelist';

describe('parseWhitelistInput', () => {
  it('should read a bare domain', () => {
    expect(parseWhitelistInput('opensea.io')).toEqual(['opensea.io']);
  });

  it('should read several domains from one comma separated list', () => {
    expect(parseWhitelistInput('opensea.io,rarible.com')).toEqual(['opensea.io', 'rarible.com']);
  });

  it('should ignore the spaces around an entry', () => {
    expect(parseWhitelistInput(' opensea.io , rarible.com ')).toEqual(['opensea.io', 'rarible.com']);
  });

  /** Pasting the url of an image should whitelist the host it came from, not the url. */
  it('should reduce a full url to its domain', () => {
    expect(parseWhitelistInput('https://images.opensea.io/some/nft.png')).toEqual(['opensea.io']);
  });

  it('should read nothing from an empty field', () => {
    expect(parseWhitelistInput('')).toEqual([]);
  });

  it('should skip an empty entry left by a trailing comma', () => {
    expect(parseWhitelistInput('opensea.io,')).toEqual(['opensea.io']);
  });
});

describe('mergeWhitelist', () => {
  it('should append what was typed to what is saved', () => {
    expect(mergeWhitelist(['opensea.io'], ['rarible.com'])).toEqual(['opensea.io', 'rarible.com']);
  });

  it('should not add a domain that is already whitelisted', () => {
    expect(mergeWhitelist(['opensea.io'], ['opensea.io'])).toEqual(['opensea.io']);
  });

  it('should add a repeated entry once', () => {
    expect(mergeWhitelist([], ['opensea.io', 'opensea.io'])).toEqual(['opensea.io']);
  });

  it('should give back what is saved when nothing was typed', () => {
    expect(mergeWhitelist(['opensea.io'], [])).toEqual(['opensea.io']);
  });
});

describe('hasWhitelistChanges', () => {
  it('should report a change when a domain was added', () => {
    expect(hasWhitelistChanges(['opensea.io'], ['opensea.io', 'rarible.com'])).toBe(true);
  });

  /** Re-adding a domain already on the list is not something to offer a save for. */
  it('should report no change when the typed domain is already saved', () => {
    const saved = ['opensea.io'];

    expect(hasWhitelistChanges(saved, mergeWhitelist(saved, parseWhitelistInput('opensea.io')))).toBe(false);
  });

  it('should report no change for an empty field', () => {
    const saved = ['opensea.io'];

    expect(hasWhitelistChanges(saved, mergeWhitelist(saved, parseWhitelistInput('')))).toBe(false);
  });

  it('should report a change when a domain was removed', () => {
    expect(hasWhitelistChanges(['opensea.io', 'rarible.com'], ['opensea.io'])).toBe(true);
  });
});
