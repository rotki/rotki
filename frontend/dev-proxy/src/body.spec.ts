import { Buffer } from 'node:buffer';
import { describe, expect, it } from 'vitest';
import { parseBody } from './body';

describe('parseBody', () => {
  it('should parse a json body', () => {
    expect(parseBody(Buffer.from('{"async_query":true}'), 'application/json'))
      .toStrictEqual({ async_query: true });
  });

  it('should parse a json body when the header carries a charset', () => {
    expect(parseBody(Buffer.from('{"async_query":true}'), 'application/json; charset=UTF-8'))
      .toStrictEqual({ async_query: true });
  });

  it('should parse a form encoded body', () => {
    expect(parseBody(Buffer.from('async_query=true&name=value'), 'application/x-www-form-urlencoded'))
      .toStrictEqual({ async_query: 'true', name: 'value' });
  });

  it('should return undefined for an empty body', () => {
    expect(parseBody(Buffer.from(''), 'application/json')).toBeUndefined();
  });

  it('should return undefined for malformed json rather than throwing', () => {
    expect(parseBody(Buffer.from('{not json'), 'application/json')).toBeUndefined();
  });

  it('should leave a content type it does not handle unparsed', () => {
    expect(parseBody(Buffer.from('binary'), 'application/octet-stream')).toBeUndefined();
  });
});
