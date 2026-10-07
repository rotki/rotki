import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { endSession } from '@/modules/core/session/session-lifecycle';
import { useMessageStore } from './use-message-store';

describe('useMessageStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('should show a message while a session is live', () => {
    const store = useMessageStore();

    store.setMessage({ description: 'saved', success: true });

    expect(store.message).toMatchObject({ description: 'saved', success: true });
  });

  it('should drop a message raised with no live session, success or error', () => {
    const store = useMessageStore();
    endSession();

    store.setMessage({ description: 'row deleted', success: true });
    store.setMessage({ description: 'delete failed' });

    expect(store.message).toBeUndefined();
  });

  it('should show a sessionless message with no live session', () => {
    const store = useMessageStore();
    endSession();

    store.setMessage({ description: 'Logout failed' }, { sessionless: true });

    expect(store.message).toMatchObject({ description: 'Logout failed', success: false });
  });

  it('should still clear the dialog with no live session', () => {
    const store = useMessageStore();
    store.setMessage({ description: 'saved', success: true });
    endSession();

    store.setMessage();

    expect(store.message).toBeUndefined();
  });
});
