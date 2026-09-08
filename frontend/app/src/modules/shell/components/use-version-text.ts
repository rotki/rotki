import type { SystemVersion } from '@shared/ipc';
import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { WebVersion } from '@/types';

/** The premium components the app loaded, absent for a non-premium user. */
interface ComponentsVersion {
  readonly version: string;
  /** The build timestamp in milliseconds, which the about screen renders as a date. */
  readonly build: number;
}

/** Everything the about screen knows about what is running. */
export interface VersionSummary {
  readonly appVersion: string;
  readonly frontendVersion: string;
  /** What the app is running on, absent until the interop call comes back. */
  readonly system?: SystemVersion | WebVersion;
  readonly components?: ComponentsVersion;
}

/**
 * Whether the app is running in a browser rather than in electron.
 *
 * @remarks
 * The interop call answers with one shape or the other and nothing labels which, so the presence
 * of `userAgent` is what separates them.
 *
 * @param system - what the interop call returned
 * @returns whether it describes a browser
 */
export function isWebVersion(system: SystemVersion | WebVersion): system is WebVersion {
  return 'userAgent' in system;
}

/**
 * The versions as one block of text, which is what the about screen copies to the clipboard for
 * pasting into a bug report.
 *
 * @remarks
 * Lines end in CRLF so the block survives being pasted into a windows editor. Only the platform
 * the app is actually running on contributes lines, and the premium components only appear when
 * they were loaded.
 *
 * @param summary - what is running
 * @returns the text to copy
 */
export function useVersionText(summary: MaybeRefOrGetter<VersionSummary>): ComputedRef<string> {
  const { t } = useI18n({ useScope: 'global' });

  return computed<string>(() => {
    const { appVersion, components, frontendVersion, system } = toValue(summary);
    const lines = [
      `${t('about.app_version')} ${appVersion}`,
      `${t('about.frontend_version')} ${frontendVersion}`,
    ];

    if (system) {
      if (isWebVersion(system)) {
        lines.push(`${t('about.platform')} ${system.platform}`, `${t('about.user_agent')} ${system.userAgent}`);
      }
      else {
        lines.push(
          `${t('about.platform')} ${system.os} ${system.arch} ${system.osVersion}`,
          `${t('about.electron')} ${system.electron}`,
        );
      }
    }

    if (components)
      lines.push(`${t('about.components.version')} ${components.version}`, `${t('about.components.build')} ${components.build}`);

    return `${lines.join('\r\n')}\r\n`;
  });
}
