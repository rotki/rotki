import { describe, expect, it } from 'vitest';
import { loginRouteFor, redirectAfterUnlock } from '@/modules/shell/layout/login-redirect';

describe('login-redirect', () => {
  describe('loginRouteFor', () => {
    it('should carry the page a logged-out navigation was headed for, query included', () => {
      expect(loginRouteFor({ fullPath: '/history/events?page=2', path: '/history/events' }))
        .toEqual({ path: '/user/login', query: { redirect: '/history/events?page=2' } });
    });

    it('should carry nothing for the app root', () => {
      expect(loginRouteFor({ fullPath: '/', path: '/' })).toBe('/user/login');
    });
  });

  describe('redirectAfterUnlock', () => {
    it('should return the app page the login was redirected from', () => {
      expect(redirectAfterUnlock({ redirect: '/history/events?page=2' })).toBe('/history/events?page=2');
    });

    it('should return nothing without a redirect', () => {
      expect(redirectAfterUnlock({})).toBeUndefined();
    });

    it.each([
      ['a login page', '/user/login'],
      ['an external address', 'https://example.com'],
      ['a protocol-relative address', '//example.com/history'],
      ['a repeated query value', ['/history', '/dashboard']],
    ])('should ignore %s', (_, redirect) => {
      expect(redirectAfterUnlock({ redirect })).toBeUndefined();
    });
  });
});
