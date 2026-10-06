import type { LocationQuery, RouteLocationRaw } from 'vue-router';

const REDIRECT_QUERY = 'redirect';

const LOGIN_PATH = '/user/login';

/**
 * The login route for a navigation that needs a session, carrying where it was headed.
 *
 * @remarks
 * A reload while logged in starts logged out until the resume finishes, so without the target the
 * resumed session lands on the dashboard instead of the page that was open.
 */
export function loginRouteFor(target: { readonly fullPath: string; readonly path: string }): RouteLocationRaw {
  if (target.path === '/')
    return LOGIN_PATH;
  return { path: LOGIN_PATH, query: { [REDIRECT_QUERY]: target.fullPath } };
}

/**
 * The page to open once an unlock is ready: the one the login was redirected from.
 *
 * @returns the target path, or `undefined` when there is none or it is not an app page
 */
export function redirectAfterUnlock(query: LocationQuery): string | undefined {
  const target = query[REDIRECT_QUERY];
  if (typeof target !== 'string')
    return undefined;

  const isAppPath = target.startsWith('/') && !target.startsWith('//') && !target.startsWith('/user');
  return isAppPath ? target : undefined;
}
