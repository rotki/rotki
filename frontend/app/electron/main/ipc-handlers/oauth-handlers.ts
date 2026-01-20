import type { LogService } from '@electron/main/log-service';
import { session } from 'electron';

const OAUTH_COOKIE_DOMAINS: readonly string[] = [
  'monerium.app',
  'monerium.dev', // sandbox environment
];

export class OAuthHandlers {
  constructor(private readonly logger: LogService) {}

  /**
   * Clears OAuth-related cookies for all configured domains.
   * Should be called on user logout and app startup to ensure clean state between users.
   */
  clearOAuthCookies = async (reason: 'startup' | 'logout' = 'logout'): Promise<void> => {
    this.logger.info(`Clearing OAuth cookies (reason: ${reason})`);

    for (const domain of OAUTH_COOKIE_DOMAINS) {
      try {
        const cookies = await session.defaultSession.cookies.get({ domain });

        for (const cookie of cookies) {
          const protocol = cookie.secure ? 'https' : 'http';
          const cookieDomain = cookie.domain?.startsWith('.') ? cookie.domain.substring(1) : cookie.domain;
          const cookieUrl = `${protocol}://${cookieDomain}${cookie.path}`;

          await session.defaultSession.cookies.remove(cookieUrl, cookie.name);
          this.logger.debug(`Removed cookie: ${cookie.name} from ${cookieDomain}`);
        }

        if (cookies.length > 0) {
          this.logger.info(`Cleared ${cookies.length} cookies for domain: ${domain}`);
        }
      }
      catch (error) {
        this.logger.error(`Failed to clear cookies for domain ${domain}:`, error);
      }
    }
  };
}
