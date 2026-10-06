import { BinaryComponent, BinaryPlatform, BinaryStatus, type UnusableBinary } from '@shared/starling/binary-types';
import { QUARANTINED_COLIBRI } from '@test/fixtures/unusable-binary';
import { describe, expect, it } from 'vitest';
import { useMissingBinaryCopy } from './use-missing-binary-copy';

function copyOf(overrides: Partial<UnusableBinary>): ReturnType<typeof useMissingBinaryCopy>['value'] {
  return useMissingBinaryCopy({ ...QUARANTINED_COLIBRI, ...overrides }).value;
}

describe('useMissingBinaryCopy', () => {
  it('should blame security software only for a missing file', () => {
    expect(copyOf({ status: BinaryStatus.MISSING }).cause).toBe('missing_binary.cause.missing');
    expect(copyOf({ status: BinaryStatus.NOT_EXECUTABLE }).cause).toBe('missing_binary.cause.not_executable');
    expect(copyOf({ status: BinaryStatus.UNREADABLE }).cause).toBe('missing_binary.cause.unreadable');
    expect(copyOf({ status: BinaryStatus.REPLACED }).cause).toBe('missing_binary.cause.replaced');
  });

  it('should name Smart App Control and policies for a file Windows refused to run', () => {
    expect(copyOf({ platform: BinaryPlatform.WINDOWS, status: BinaryStatus.NOT_EXECUTABLE }).cause)
      .toBe('missing_binary.cause.not_executable_windows');
  });

  it('should give a header, title and subtitle of its own to every status', () => {
    const statuses = Object.values(BinaryStatus);
    const copies = statuses.map(status => copyOf({ component: BinaryComponent.CORE, status }));

    for (const field of ['header', 'title', 'subtitle'] as const)
      expect(new Set(copies.map(copy => copy[field])).size).toBe(statuses.length);
  });

  it('should tell Windows users to allow the file on the device after restoring it', () => {
    expect(copyOf({ platform: BinaryPlatform.WINDOWS }).steps).toStrictEqual([
      'missing_binary.steps.update_definitions',
      'missing_binary.steps.restore_windows',
      'missing_binary.steps.exclude',
      'missing_binary.steps.reinstall',
    ]);
  });

  it('should point macOS users at a reinstall, since macOS keeps no quarantine to restore from', () => {
    expect(copyOf({ platform: BinaryPlatform.MACOS }).steps).toStrictEqual([
      'missing_binary.steps.update_definitions',
      'missing_binary.steps.restore',
      'missing_binary.steps.exclude',
      'missing_binary.steps.reinstall_macos',
    ]);
  });

  it('should not send a blocked file to the quarantine', () => {
    for (const status of [BinaryStatus.NOT_EXECUTABLE, BinaryStatus.UNREADABLE]) {
      expect(copyOf({ status }).steps).toStrictEqual([
        'missing_binary.steps.allow',
        'missing_binary.steps.reinstall_otherwise',
      ]);
    }
  });

  it('should only ask for a restart after an update', () => {
    const copy = copyOf({ status: BinaryStatus.REPLACED });

    expect(copy.steps).toStrictEqual([]);
    expect(copy.recovery).toBe('missing_binary.recovery.restart');
  });
});
