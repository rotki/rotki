import { describe, expect, it } from 'vitest';
import { WebsocketMessage } from '@/modules/core/messaging/messages';
import { SocketMessageType } from '@/modules/core/messaging/types/base';

const started = {
  name: 'Query history of my kraken exchange',
  startedAt: 1700000000,
  status: 'started',
};

describe('background task messages', () => {
  it('should accept a background task status as a websocket message', () => {
    const result = WebsocketMessage.safeParse({ data: started, type: SocketMessageType.BACKGROUND_TASK_STATUS });
    expect(result.success).toBe(true);
  });

  it.each(['finished', 'failed', 'cancelled'])('should accept a task ending as %s', (status) => {
    const result = WebsocketMessage.safeParse({ data: { ...started, status }, type: SocketMessageType.BACKGROUND_TASK_STATUS });
    expect(result.success).toBe(true);
  });

  it('should reject a status the backend does not send', () => {
    const result = WebsocketMessage.safeParse({
      data: { ...started, status: 'paused' },
      type: SocketMessageType.BACKGROUND_TASK_STATUS,
    });
    expect(result.success).toBe(false);
  });
});
