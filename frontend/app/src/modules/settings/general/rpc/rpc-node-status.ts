export const NODE_STATUS = {
  CONNECTED: 'connected',
  COOLING_DOWN: 'cooling_down',
  FAILED: 'failed',
  READY: 'ready',
} as const;

export type NodeStatus = typeof NODE_STATUS[keyof typeof NODE_STATUS];
