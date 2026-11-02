import { describe, expect, it } from 'vitest';
import { WebsocketMessage } from '@/modules/core/messaging/messages';
import { SocketMessageType } from '@/modules/core/messaging/types/base';
import { BackgroundTaskKind, backgroundTaskKindOf } from './background-task-types';

const started = {
  id: 4,
  kind: 'exchange_history',
  name: 'Query history of my kraken exchange',
  startedAt: 1700000000,
  status: 'started',
  subject: { location: 'kraken', name: 'my kraken' },
};

describe('background task messages', () => {
  it('should accept a background task status as a websocket message', () => {
    const result = WebsocketMessage.safeParse({ data: started, type: SocketMessageType.BACKGROUND_TASK_STATUS });
    expect(result.success).toBe(true);
  });

  it('should accept a failure that carries its error', () => {
    const result = WebsocketMessage.safeParse({
      data: { ...started, error: 'kraken is down', status: 'failed' },
      type: SocketMessageType.BACKGROUND_TASK_STATUS,
    });
    expect(result.success).toBe(true);
  });

  it('should reject a status the backend does not send', () => {
    const result = WebsocketMessage.safeParse({
      data: { ...started, status: 'paused' },
      type: SocketMessageType.BACKGROUND_TASK_STATUS,
    });
    expect(result.success).toBe(false);
  });

  it('should accept a kind this build does not know and read it as other', () => {
    const result = WebsocketMessage.safeParse({
      data: { ...started, kind: 'something_new' },
      type: SocketMessageType.BACKGROUND_TASK_STATUS,
    });
    expect(result.success).toBe(true);
    expect(backgroundTaskKindOf('something_new')).toBe(BackgroundTaskKind.OTHER);
    expect(backgroundTaskKindOf('exchange_history')).toBe(BackgroundTaskKind.EXCHANGE_HISTORY);
  });
});
