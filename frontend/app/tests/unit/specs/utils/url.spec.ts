import { getDomain } from '@/utils/url';
import { describe, expect, it } from 'vitest';

describe('utils/url', () => {
  it('default', () => {
    expect(getDomain('https://www.google.com')).toEqual('google.com');
    expect(getDomain('http://www.google.com')).toEqual('google.com');
    expect(getDomain('www.google.com')).toEqual('google.com');
    expect(getDomain('google.com')).toEqual('google.com');
    expect(getDomain('https://www.images.google.com')).toEqual('google.com');
    expect(getDomain('https://www.images.google.co.id')).toEqual('google.co.id');
    expect(getDomain('https://www.images.google.ac.gov.br')).toEqual('google.ac.gov.br');
    expect(getDomain('not_an_url')).toEqual('not_an_url');
    expect(getDomain('.co.id')).toEqual('.co.id');
  });
});
