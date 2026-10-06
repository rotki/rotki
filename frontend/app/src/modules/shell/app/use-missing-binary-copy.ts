import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import { BinaryPlatform, BinaryStatus, type UnusableBinary } from '@shared/starling/binary-types';

interface MissingBinaryCopy {
  header: string;
  title: string;
  subtitle: string;
  cause: string;
  /** Leads the steps, or stands alone when there are none. */
  recovery: string;
  steps: string[];
}

/**
 * The text of the screen explaining an unusable bundled binary.
 *
 * @remarks
 * Each status has its own cause, because a quarantine, a blocked file and an update installed
 * while rotki ran each need a different next step. A missing file gets steps for the platform it
 * went missing on: Windows Security needs Allow on device after a restore, and macOS keeps no
 * quarantine of its own to restore from.
 */
export function useMissingBinaryCopy(binary: MaybeRefOrGetter<UnusableBinary>): ComputedRef<MissingBinaryCopy> {
  const { t } = useI18n({ useScope: 'global' });

  function missingSteps(platform: BinaryPlatform): string[] {
    switch (platform) {
      case BinaryPlatform.WINDOWS:
        return [
          t('missing_binary.steps.update_definitions'),
          t('missing_binary.steps.restore_windows'),
          t('missing_binary.steps.exclude'),
          t('missing_binary.steps.reinstall'),
        ];
      case BinaryPlatform.MACOS:
        return [
          t('missing_binary.steps.update_definitions'),
          t('missing_binary.steps.restore'),
          t('missing_binary.steps.exclude'),
          t('missing_binary.steps.reinstall_macos'),
        ];
      case BinaryPlatform.LINUX:
        return [
          t('missing_binary.steps.update_definitions'),
          t('missing_binary.steps.restore'),
          t('missing_binary.steps.exclude'),
          t('missing_binary.steps.reinstall'),
        ];
    }
  }

  function blockedSteps(): string[] {
    return [t('missing_binary.steps.allow'), t('missing_binary.steps.reinstall_otherwise')];
  }

  function copyFor({ component, platform, status }: UnusableBinary): MissingBinaryCopy {
    switch (status) {
      case BinaryStatus.MISSING:
        return {
          header: t('missing_binary.header.missing'),
          title: t('missing_binary.title.missing', { component }),
          subtitle: t('missing_binary.subtitle.missing'),
          cause: t('missing_binary.cause.missing'),
          recovery: t('missing_binary.recovery.get_back'),
          steps: missingSteps(platform),
        };
      case BinaryStatus.NOT_EXECUTABLE:
        return {
          header: t('missing_binary.header.not_executable'),
          title: t('missing_binary.title.not_executable', { component }),
          subtitle: t('missing_binary.subtitle.present'),
          cause: platform === BinaryPlatform.WINDOWS
            ? t('missing_binary.cause.not_executable_windows')
            : t('missing_binary.cause.not_executable'),
          recovery: t('missing_binary.recovery.fix'),
          steps: blockedSteps(),
        };
      case BinaryStatus.UNREADABLE:
        return {
          header: t('missing_binary.header.unreadable'),
          title: t('missing_binary.title.unreadable', { component }),
          subtitle: t('missing_binary.subtitle.folder'),
          cause: t('missing_binary.cause.unreadable'),
          recovery: t('missing_binary.recovery.fix'),
          steps: blockedSteps(),
        };
      case BinaryStatus.REPLACED:
        return {
          header: t('missing_binary.header.replaced'),
          title: t('missing_binary.title.replaced', { component }),
          subtitle: t('missing_binary.subtitle.replaced'),
          cause: t('missing_binary.cause.replaced'),
          recovery: t('missing_binary.recovery.restart'),
          steps: [],
        };
    }
  }

  return computed<MissingBinaryCopy>(() => copyFor(toValue(binary)));
}
