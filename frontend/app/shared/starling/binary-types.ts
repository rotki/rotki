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
  NOT_EXECUTABLE: 'not-executable',
} as const;

export type BinaryStatus = typeof BinaryStatus[keyof typeof BinaryStatus];

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
  /** Set by the main process, which knows the platform for certain; the recovery steps name Windows Security on it. */
  onWindows: boolean;
  path: string;
  status: BinaryStatus;
}
