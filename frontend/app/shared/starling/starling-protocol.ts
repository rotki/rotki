/**
 * The wire vocabulary of the starling control channel: the methods we may call,
 * the events starling pushes back, and the services both address.
 *
 * Every one of these is a string starling matches exactly, so a typo is only
 * discoverable at runtime as an unknown-method error. Naming them here lets the
 * compiler reject a bad one at the call site instead.
 */

export const StarlingMethod = {
  RESTART: 'restart',
  SET_SERVICE_AUTOSTART: 'setServiceAutostart',
  START: 'start',
  START_SERVICE: 'startService',
  STATUS: 'status',
  STOP: 'stop',
  STOP_SERVICE: 'stopService',
} as const;

export type StarlingMethod = typeof StarlingMethod[keyof typeof StarlingMethod];

/**
 * Notifications starling pushes without an id. These arrive over the wire, so a
 * received method is a plain string until it is matched against one of these —
 * an unrecognised event is logged and ignored, never trusted.
 */
export const StarlingEvent = {
  CRASHED: 'event.crashed',
  READY: 'event.ready',
  RESTARTING: 'event.restarting',
  STOPPED: 'event.stopped',
} as const;

export type StarlingEvent = typeof StarlingEvent[keyof typeof StarlingEvent];

export const StarlingService = {
  COLIBRI: 'colibri',
  CORE: 'core',
  MCP: 'mcp',
  PROXY: 'proxy',
} as const;

export type StarlingService = typeof StarlingService[keyof typeof StarlingService];
