// @vitest-environment node
import { describe, expect, it } from 'vitest';
import { summarizeUpdaterError } from './updater-error';

/**
 * The seam: what of an electron-updater error reaches the log. Its messages carry the whole
 * HTTP response, which for the releases feed is every release note, so only the first line may.
 */
describe('summarizeUpdaterError', () => {
  it('should keep only the first line of a multi-line error', () => {
    const error = new Error([
      'Cannot parse releases feed: Error: Unable to find latest version on GitHub: HttpError: 504',
      '"method: GET url: https://github.com/rotki/rotki/releases/latest',
      'Data:',
      '<li>rotki will now support blockscout and routescan as fallback indexers</li>',
    ].join('\n'));

    expect(summarizeUpdaterError(error)).toBe(
      'Cannot parse releases feed: Error: Unable to find latest version on GitHub: HttpError: 504 (details truncated)',
    );
  });

  it('should keep a single line error as it is', () => {
    expect(summarizeUpdaterError(new Error('net::ERR_INTERNET_DISCONNECTED'))).toBe('net::ERR_INTERNET_DISCONNECTED');
  });

  it('should cap a very long first line', () => {
    const summary = summarizeUpdaterError(`Error: ${'x'.repeat(5000)}`);

    expect(summary).toHaveLength(500 + '… (truncated)'.length);
    expect(summary.endsWith('… (truncated)')).toBe(true);
  });

  it('should accept a non error value', () => {
    expect(summarizeUpdaterError('plain\nmessage')).toBe('plain (details truncated)');
    expect(summarizeUpdaterError(undefined)).toBe('undefined');
  });
});
