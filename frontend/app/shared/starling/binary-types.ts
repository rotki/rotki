/**
 * What the main process reports about a bundled executable it cannot run.
 *
 * @remarks
 * Kept free of imports so it can be shared by the renderer, the electron main
 * process and the node-side scripts, whose tsconfig projects do not overlap.
 */

/** The bundled executables rotki ships and cannot run without. */
export const BinaryComponent = {
  COLIBRI: 'colibri',
  CORE: 'rotki-core',
  STARLING: 'starling',
} as const;

export type BinaryComponent = typeof BinaryComponent[keyof typeof BinaryComponent];

export const BinaryStatus = {
  MISSING: 'missing',
  /** The file is there, but the system refuses to run it. */
  NOT_EXECUTABLE: 'not-executable',
  /** The core starling runs is gone and a different version sits in its place: an update, not a quarantine. */
  REPLACED: 'replaced',
  /** The folder holding the core cannot be listed, so whether the core is there is unknown. */
  UNREADABLE: 'unreadable',
} as const;

export type BinaryStatus = typeof BinaryStatus[keyof typeof BinaryStatus];

/** The platform a report was made on, which decides the recovery steps a user is given. */
export const BinaryPlatform = {
  LINUX: 'linux',
  MACOS: 'macos',
  WINDOWS: 'windows',
} as const;

export type BinaryPlatform = typeof BinaryPlatform[keyof typeof BinaryPlatform];

/**
 * A bundled executable that is not there, or is there and cannot be run.
 *
 * @remarks
 * Travels beside the startup error text so the renderer can name the component
 * and its path in the user's own language, instead of rendering a sentence the
 * main process built in English.
 */
export interface UnusableBinary {
  component: BinaryComponent;
  /** Set by the main process, which knows the platform for certain. */
  platform: BinaryPlatform;
  path: string;
  status: BinaryStatus;
}
