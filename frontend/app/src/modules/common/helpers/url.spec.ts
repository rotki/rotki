import { describe, expect, it } from 'vitest';
import { getDomain } from '@/modules/common/helpers/url';

describe('url-utils', () => {
  it('should handle default case', () => {
    expect(getDomain('https://www.google.com')).toBe('google.com');
    expect(getDomain('http://www.google.com')).toBe('google.com');
    expect(getDomain('www.google.com')).toBe('google.com');
    expect(getDomain('google.com')).toBe('google.com');
    expect(getDomain('https://www.images.google.com')).toBe('google.com');
    expect(getDomain('https://www.images.google.co.id')).toBe('google.co.id');
    expect(getDomain('https://www.images.google.ac.gov.br')).toBe('google.ac.gov.br');
    expect(getDomain('not_an_url')).toBe('not_an_url');
    expect(getDomain('.co.id')).toBe('.co.id');
  });
});
