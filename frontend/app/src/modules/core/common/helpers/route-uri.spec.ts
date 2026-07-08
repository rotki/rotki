import { describe, expect, it } from 'vitest';
import { fromUriEncoded, toUriEncoded } from './route-uri';

describe('toUriEncoded', () => {
  it('should encode a single key/value pair', () => {
    expect(toUriEncoded({ foo: 'bar' })).toBe(encodeURIComponent('foo=bar'));
  });

  it('should join multiple params with an ampersand before encoding', () => {
    expect(toUriEncoded({ a: '1', b: '2' })).toBe(encodeURIComponent('a=1&b=2'));
  });

  it('should stringify null entries as the literal "undefined"', () => {
    expect(toUriEncoded({ missing: null })).toBe(encodeURIComponent('missing=undefined'));
  });

  it('should return an empty string for an empty query', () => {
    expect(toUriEncoded({})).toBe('');
  });
});

describe('fromUriEncoded', () => {
  it('should decode a single key/value pair', () => {
    expect(fromUriEncoded(encodeURIComponent('foo=bar'))).toEqual({ foo: 'bar' });
  });

  it('should decode multiple params', () => {
    expect(fromUriEncoded(encodeURIComponent('a=1&b=2'))).toEqual({ a: '1', b: '2' });
  });

  it('should round-trip values produced by toUriEncoded', () => {
    const params = { chain: 'ethereum', page: '3' };
    expect(fromUriEncoded(toUriEncoded(params))).toEqual(params);
  });

  it('should return an empty object for an empty string', () => {
    expect(fromUriEncoded('')).toEqual({});
  });
});
