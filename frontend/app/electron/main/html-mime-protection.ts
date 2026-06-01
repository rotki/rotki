import type { LogService } from '@electron/main/log-service';
import { execFileSync } from 'node:child_process';
import process from 'node:process';

const HTML_MIME_TYPE = 'text/html';
const ROTKI_DESKTOP = 'rotki.desktop';
// Cap each xdg-* invocation so a hanging tool (slow dbus/portal, networked home)
// cannot freeze the startup path while we wait for it.
const XDG_TIMEOUT_MS = 3000;

function runXdg(command: string, args: string[], logger: LogService): string | undefined {
  try {
    const result = execFileSync(command, args, { encoding: 'utf8', timeout: XDG_TIMEOUT_MS });
    const value = result.trim();
    return value.length > 0 ? value : undefined;
  }
  catch (error) {
    logger.warn(`Failed to run ${command} ${args.join(' ')}`, error);
    return undefined;
  }
}

function queryHtmlHandler(logger: LogService): string | undefined {
  return runXdg('xdg-mime', ['query', 'default', HTML_MIME_TYPE], logger);
}

function queryDefaultWebBrowser(logger: LogService): string | undefined {
  const browser = runXdg('xdg-settings', ['get', 'default-web-browser'], logger);
  return browser && browser !== ROTKI_DESKTOP ? browser : undefined;
}

function restoreHtmlHandler(handler: string, logger: LogService): void {
  try {
    execFileSync('xdg-mime', ['default', handler, HTML_MIME_TYPE], { timeout: XDG_TIMEOUT_MS });
    logger.info(`Restored the default ${HTML_MIME_TYPE} handler to ${handler}`);
  }
  catch (error) {
    logger.warn(`Failed to restore the default ${HTML_MIME_TYPE} handler to ${handler}`, error);
  }
}

/**
 * Runs `register` while protecting the system's text/html association (issue #12323).
 *
 * On Linux/GNOME with old xdg-utils (<1.2.0, e.g. Ubuntu 24.04's 1.1.3), Electron's
 * app.setAsDefaultProtocolClient shells out to `xdg-settings set
 * default-url-scheme-handler`, whose buggy GNOME path (xdg-utils#180) also rewrites
 * the default text/html handler in ~/.config/mimeapps.list. Registering rotki:// thus
 * hijacks HTML files.
 *
 * We snapshot the text/html handler before registering and restore it if the call
 * changed it to rotki.desktop. We also heal users already corrupted by a previous
 * launch (snapshot is already rotki.desktop / unavailable) by falling back to the
 * system default web browser, which is the correct text/html handler.
 *
 * On non-Linux platforms `register` is run unchanged; the bug is xdg-specific.
 *
 * `register` returns whether it actually attempted to (re)register the protocol.
 * When it returns false (already registered / nothing to do) we skip the second
 * snapshot, since only an actual registration can hijack text/html.
 */
export function protectHtmlAssociation(logger: LogService, register: () => boolean): void {
  if (process.platform !== 'linux') {
    register();
    return;
  }

  const before = queryHtmlHandler(logger);

  const registered = register();

  // Only an actual registration can change text/html; if we skipped it the state
  // is unchanged, so reuse `before` instead of spawning a second query.
  const after = registered ? queryHtmlHandler(logger) : before;

  // Only act if text/html ended up pointing at rotki; anything else we leave
  // untouched so we can never make the association worse.
  if (after !== ROTKI_DESKTOP)
    return;

  const restoreTo = before && before !== ROTKI_DESKTOP ? before : queryDefaultWebBrowser(logger);

  if (restoreTo) {
    logger.warn(`The default ${HTML_MIME_TYPE} handler was hijacked to ${ROTKI_DESKTOP}; restoring it (xdg-utils#180)`);
    restoreHtmlHandler(restoreTo, logger);
  }
  else {
    logger.warn(`The default ${HTML_MIME_TYPE} handler is ${ROTKI_DESKTOP} but no prior handler could be determined to restore it`);
  }
}
