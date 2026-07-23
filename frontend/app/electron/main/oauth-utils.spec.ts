import { assert } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { parseToken } from './oauth-utils';

const BASE = 'rotki://auth';

describe('parseToken', () => {
  it('should parse a success callback with all parameters', () => {
    const result = parseToken(`${BASE}/success?access_token=abc&refresh_token=ref&service=google&expires_in=3600`);
    assert(result.success);
    expect(result).toStrictEqual({
      success: true,
      service: 'google',
      accessToken: 'abc',
      refreshToken: 'ref',
      expiresIn: 3600,
    });
  });

  it('should default service to google and leave optionals undefined on a minimal success', () => {
    const result = parseToken(`${BASE}/success?access_token=abc`);
    assert(result.success);
    expect(result.service).toBe('google');
    expect(result.refreshToken).toBeUndefined();
    expect(result.expiresIn).toBeUndefined();
  });

  it('should treat a non-numeric expires_in as undefined', () => {
    const result = parseToken(`${BASE}/success?access_token=abc&expires_in=not-a-number`);
    assert(result.success);
    expect(result.expiresIn).toBeUndefined();
  });

  it('should return a failure when the success callback has no access_token', () => {
    const result = parseToken(`${BASE}/success?service=dropbox`);
    assert(!result.success);
    expect(result.service).toBe('dropbox');
    expect(result.error.message).toBe('Failed to parse OAuth callback URL. missing access_token');
  });

  it('should default service to unknown when access_token and service are both missing', () => {
    const result = parseToken(`${BASE}/success`);
    assert(!result.success);
    expect(result.service).toBe('unknown');
  });

  it('should parse a failure callback with an error message', () => {
    const result = parseToken(`${BASE}/failure?error=access_denied&service=google`);
    assert(!result.success);
    expect(result.service).toBe('google');
    expect(result.error.message).toBe('access_denied');
  });

  it('should fall back to invalid-path when a failure callback has no error', () => {
    const url = `${BASE}/failure`;
    const result = parseToken(url);
    assert(!result.success);
    expect(result.service).toBe('unknown');
    expect(result.error.message).toBe(`Invalid path in OAuth callback URL: ${url}`);
  });

  it('should return invalid-path for an unrecognized pathname', () => {
    const url = `${BASE}/whatever?access_token=abc`;
    const result = parseToken(url);
    assert(!result.success);
    expect(result.error.message).toBe(`Invalid path in OAuth callback URL: ${url}`);
  });

  it('should return a parse failure for a malformed URL', () => {
    const result = parseToken('::: not a url :::');
    assert(!result.success);
    expect(result.service).toBe('unknown');
    expect(result.error.message).toMatch(/^Failed to parse OAuth callback URL:/);
  });
});
