import { StarlingServiceStatus } from '@shared/ipc';
import { z } from 'zod';

/**
 * The states starling reports over the wire. `Unavailable` is the app's own
 * sentinel for "there is no supervisor answering", so it is deliberately absent:
 * a service that arrives as `Unavailable` would mean starling contradicted
 * itself.
 */
const ReportedServiceState = z.enum([
  StarlingServiceStatus.DEGRADED,
  StarlingServiceStatus.FAILED,
  StarlingServiceStatus.IDLE,
  StarlingServiceStatus.READY,
  StarlingServiceStatus.RESTARTING,
  StarlingServiceStatus.SPAWNING,
  StarlingServiceStatus.STOPPED,
  StarlingServiceStatus.STOPPING,
  StarlingServiceStatus.WAITING_READY,
]);

export const ControlServiceStatus = z.object({
  autostart: z.boolean(),
  lastError: z.string().nullish(),
  name: z.string(),
  restarts: z.number(),
  state: ReportedServiceState,
});

export type ControlServiceStatus = z.infer<typeof ControlServiceStatus>;

export const ControlStatus = z.object({
  services: z.array(ControlServiceStatus),
});

export type ControlStatus = z.infer<typeof ControlStatus>;

/**
 * What `GET /_control` answers when the endpoint is mounted. A deployment
 * without the session cookie configured serves 404 instead, which is what makes
 * this a reliable availability probe rather than a claim the app has to trust.
 */
export const ControlCapabilities = z.object({
  available: z.literal(true),
  methods: z.array(z.string()),
});

export type ControlCapabilities = z.infer<typeof ControlCapabilities>;

/**
 * A JSON-RPC 2.0 reply. The transport answers 200 even for a refused operation
 * (that is the protocol), so `error` is the only thing that says whether the
 * call did anything.
 */
export const ControlRpcResponse = z.object({
  error: z.object({
    code: z.number(),
    message: z.string(),
  }).optional(),
  result: z.unknown().optional(),
});

export type ControlRpcResponse = z.infer<typeof ControlRpcResponse>;
