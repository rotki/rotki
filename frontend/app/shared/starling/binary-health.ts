/**
 * Whether the executables a packaged rotki ships are still on disk and still
 * runnable.
 *
 * @remarks
 * Security software quarantines false positives, and an unsigned native binary
 * is routine false-positive material. Rather than let that surface as a raw
 * `ENOENT` from a spawn, every packaged binary is inspected up front and again
 * whenever the backend dies, so the failure can be reported as the file it is
 * about. An antivirus kill can exit 0, so the exit code cannot be the
 * discriminator - only the file's absence can.
 */
import fs from 'node:fs';
import process from 'node:process';
import { BinaryComponent, BinaryStatus, type UnusableBinary } from './binary-types';
import { resolvePackagedColibri, resolveStarlingBinary } from './starling-launchers';
import { findCoreBinary, packagedBackendDirectory } from './starling-paths';

function report(component: BinaryComponent, path: string, status: BinaryStatus): UnusableBinary {
  return { component, onWindows: process.platform === 'win32', path, status };
}

/** Whether an error came from the filesystem (it carries an errno `code`) rather than from our own checks. */
function isFilesystemError(error: unknown): boolean {
  return error instanceof Error && 'code' in error && typeof error.code === 'string';
}

/**
 * Inspect one binary.
 *
 * @remarks
 * `X_OK` is meaningless on Windows, where `accessSync` only tells us the file
 * exists, so `not-executable` is in practice a POSIX answer.
 */
function inspectBinary(component: BinaryComponent, binary: string): UnusableBinary | undefined {
  if (!fs.existsSync(binary))
    return report(component, binary, BinaryStatus.MISSING);

  try {
    fs.accessSync(binary, fs.constants.X_OK);
  }
  catch {
    return report(component, binary, BinaryStatus.NOT_EXECUTABLE);
  }

  return undefined;
}

/**
 * The packaged core, reported against the directory searched rather than a file:
 * the whole `backend/` directory can be what went, and the binary carries a
 * version in its name that the user has no way to guess.
 *
 * @remarks
 * `findCoreBinary` throws in two ways. A filesystem error means the directory
 * cannot be read, which is how security software locking it looks, so it is
 * reported as unusable. A plain error means a broken upgrade left two binaries:
 * not a quarantine, so it is passed over and left to surface where the
 * invocation is built, whose error handling reports it. Nothing is rethrown,
 * since this runs inside the spawn path and the process event handlers.
 */
function inspectCore(): UnusableBinary | undefined {
  const directory = packagedBackendDirectory();
  let resolved: ReturnType<typeof findCoreBinary>;
  try {
    resolved = findCoreBinary(directory);
  }
  catch (error) {
    return isFilesystemError(error)
      ? report(BinaryComponent.CORE, directory, BinaryStatus.NOT_EXECUTABLE)
      : undefined;
  }

  if (!resolved)
    return report(BinaryComponent.CORE, directory, BinaryStatus.MISSING);

  return inspectBinary(BinaryComponent.CORE, resolved.binary);
}

/**
 * The first packaged binary that cannot be run, starling first.
 *
 * @remarks
 * starling leads because it is the one Electron spawns itself: if it is the file
 * that went, there is no supervisor left to report anything and this check is
 * the only thing standing between the user and a bare io error.
 *
 * @param launchedCore - the core binary starling was started with. Once there is
 * one, that exact file is what matters: an upgrade can swap in a new version
 * beside it, and a fresh search of the directory would find that one healthy
 * while starling keeps respawning the old path. Before a launch the directory is
 * searched.
 */
export function findUnusableBinary(launchedCore?: string): UnusableBinary | undefined {
  return inspectBinary(BinaryComponent.STARLING, resolveStarlingBinary())
    ?? (launchedCore ? inspectBinary(BinaryComponent.CORE, launchedCore) : inspectCore())
    ?? inspectBinary(BinaryComponent.COLIBRI, resolvePackagedColibri().binary);
}
