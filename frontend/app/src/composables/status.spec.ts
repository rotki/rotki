import { beforeEach, describe, expect, it } from 'vitest';
import { Section, Status } from '@/modules/common/status';
import { useStatusStore } from '@/modules/common/use-status-store';
import { waitUntilIdle } from './status';

describe('waitUntilIdle', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('should resolve immediately when section is not loading', async () => {
    const promise = waitUntilIdle(Section.BLOCKCHAIN);
    await expect(promise).resolves.toBeUndefined();
  });

  it('should resolve immediately when subsection is not loading', async () => {
    const store = useStatusStore();
    store.setStatus({ section: Section.BLOCKCHAIN, status: Status.LOADING, subsection: 'eth' });

    const promise = waitUntilIdle(Section.BLOCKCHAIN, 'btc');
    await expect(promise).resolves.toBeUndefined();
  });

  it('should wait until section stops loading', async () => {
    const store = useStatusStore();
    store.setStatus({ section: Section.BLOCKCHAIN, status: Status.LOADING });

    let resolved = false;
    const promise = waitUntilIdle(Section.BLOCKCHAIN).then(() => {
      resolved = true;
    });

    await nextTick();
    expect(resolved).toBe(false);

    store.setStatus({ section: Section.BLOCKCHAIN, status: Status.LOADED });
    await promise;
    expect(resolved).toBe(true);
  });

  it('should wait until subsection stops loading', async () => {
    const store = useStatusStore();
    store.setStatus({ section: Section.BLOCKCHAIN, status: Status.LOADING, subsection: 'eth' });

    let resolved = false;
    const promise = waitUntilIdle(Section.BLOCKCHAIN, 'eth').then(() => {
      resolved = true;
    });

    await nextTick();
    expect(resolved).toBe(false);

    store.setStatus({ section: Section.BLOCKCHAIN, status: Status.LOADED, subsection: 'eth' });
    await promise;
    expect(resolved).toBe(true);
  });

  it('should resolve when status transitions from REFRESHING to LOADED', async () => {
    const store = useStatusStore();
    store.setStatus({ section: Section.BLOCKCHAIN, status: Status.REFRESHING });

    let resolved = false;
    const promise = waitUntilIdle(Section.BLOCKCHAIN).then(() => {
      resolved = true;
    });

    await nextTick();
    expect(resolved).toBe(false);

    store.setStatus({ section: Section.BLOCKCHAIN, status: Status.LOADED });
    await promise;
    expect(resolved).toBe(true);
  });
});
