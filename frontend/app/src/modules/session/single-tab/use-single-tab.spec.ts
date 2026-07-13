import type { UseSingleTabReturn } from './use-single-tab';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const isPackaged = ref<boolean>(false);
const reload = vi.fn();

vi.mock('@/modules/shell/app/use-electron-interop', () => ({
  useInterop: (): object => ({
    get isPackaged(): boolean {
      return get(isPackaged);
    },
  }),
}));

interface TabMessage {
  type: 'claim' | 'release';
  tabId: string;
}

class FakeBroadcastChannel {
  static instances: FakeBroadcastChannel[] = [];
  readonly name: string;
  onmessage: ((event: MessageEvent<TabMessage>) => void) | null = null;
  readonly posted: TabMessage[] = [];
  closed = false;

  constructor(name: string) {
    this.name = name;
    FakeBroadcastChannel.instances.push(this);
  }

  postMessage(data: TabMessage): void {
    this.posted.push(data);
  }

  close(): void {
    this.closed = true;
  }
}

const originalAddEventListener = window.addEventListener.bind(window);
let pagehideHandlers: EventListener[] = [];

async function loadSingleTab(): Promise<UseSingleTabReturn> {
  vi.resetModules();
  const module = await import('./use-single-tab');
  return module.useSingleTab();
}

function receive(channel: FakeBroadcastChannel, data: TabMessage): void {
  channel.onmessage?.({ data } as MessageEvent<TabMessage>);
}

function postedOfType(channel: FakeBroadcastChannel, type: TabMessage['type']): TabMessage[] {
  return channel.posted.filter(message => message.type === type);
}

describe('useSingleTab', () => {
  beforeEach(() => {
    set(isPackaged, false);
    reload.mockClear();
    FakeBroadcastChannel.instances = [];
    pagehideHandlers = [];
    vi.stubGlobal('BroadcastChannel', FakeBroadcastChannel);
    vi.stubGlobal('location', { reload });
    // Capture the pagehide listeners each load registers so they can be torn down per test —
    // the createGlobalState singleton never disposes, so they would otherwise accumulate.
    vi.spyOn(window, 'addEventListener').mockImplementation(((type: string, handler: EventListener, options?: unknown): void => {
      if (type === 'pagehide')
        pagehideHandlers.push(handler);
      originalAddEventListener(type, handler, options as AddEventListenerOptions);
    }) as typeof window.addEventListener);
  });

  afterEach(() => {
    for (const handler of pagehideHandlers)
      window.removeEventListener('pagehide', handler);
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  it('should be supported in the web/docker build with BroadcastChannel available', async () => {
    const { supported } = await loadSingleTab();
    expect(supported).toBe(true);
  });

  it('should broadcast a claim and keep this tab active', async () => {
    const { claim, isActiveTab } = await loadSingleTab();
    claim();

    expect(FakeBroadcastChannel.instances).toHaveLength(1);
    const [channel] = FakeBroadcastChannel.instances;
    expect(channel.name).toBe('rotki.session.single-tab');
    expect(postedOfType(channel, 'claim')).toHaveLength(1);
    expect(get(isActiveTab)).toBe(true);
  });

  it('should deactivate this tab when another tab claims the session', async () => {
    const { claim, isActiveTab } = await loadSingleTab();
    claim();
    const [channel] = FakeBroadcastChannel.instances;

    receive(channel, { tabId: 'another-tab', type: 'claim' });

    expect(get(isActiveTab)).toBe(false);
  });

  it('should ignore its own claim echoed back on the channel', async () => {
    const { claim, isActiveTab } = await loadSingleTab();
    claim();
    const [channel] = FakeBroadcastChannel.instances;
    const ownTabId = channel.posted[0].tabId;

    receive(channel, { tabId: ownTabId, type: 'claim' });

    expect(get(isActiveTab)).toBe(true);
  });

  it('should reactivate and post a fresh claim when it claims again after takeover', async () => {
    const { claim, isActiveTab } = await loadSingleTab();
    claim();
    const [channel] = FakeBroadcastChannel.instances;
    receive(channel, { tabId: 'another-tab', type: 'claim' });
    expect(get(isActiveTab)).toBe(false);

    claim();

    expect(get(isActiveTab)).toBe(true);
    expect(postedOfType(channel, 'claim')).toHaveLength(2);
  });

  it('should claim and reload on reclaim', async () => {
    const { reclaim } = await loadSingleTab();
    reclaim();

    const [channel] = FakeBroadcastChannel.instances;
    expect(postedOfType(channel, 'claim')).toHaveLength(1);
    expect(reload).toHaveBeenCalledOnce();
  });

  it('should take over after a release once it has been superseded', async () => {
    const { claim, isActiveTab } = await loadSingleTab();
    claim();
    const [channel] = FakeBroadcastChannel.instances;
    receive(channel, { tabId: 'another-tab', type: 'claim' });
    expect(get(isActiveTab)).toBe(false);

    vi.useFakeTimers();
    receive(channel, { tabId: 'another-tab', type: 'release' });
    await vi.advanceTimersByTimeAsync(400);

    expect(reload).toHaveBeenCalledOnce();
  });

  it('should ignore a release while it is still the active tab', async () => {
    const { claim } = await loadSingleTab();
    claim();
    const [channel] = FakeBroadcastChannel.instances;

    vi.useFakeTimers();
    receive(channel, { tabId: 'another-tab', type: 'release' });
    await vi.advanceTimersByTimeAsync(400);

    expect(reload).not.toHaveBeenCalled();
  });

  it('should cancel a queued takeover when another tab claims first', async () => {
    const { claim, isActiveTab } = await loadSingleTab();
    claim();
    const [channel] = FakeBroadcastChannel.instances;
    receive(channel, { tabId: 'tab-a', type: 'claim' });

    vi.useFakeTimers();
    receive(channel, { tabId: 'tab-a', type: 'release' });
    receive(channel, { tabId: 'tab-b', type: 'claim' });
    await vi.advanceTimersByTimeAsync(400);

    expect(reload).not.toHaveBeenCalled();
    expect(get(isActiveTab)).toBe(false);
  });

  it('should broadcast a release on logout when it is the active tab', async () => {
    const { claim, release } = await loadSingleTab();
    claim();
    const [channel] = FakeBroadcastChannel.instances;

    release();

    expect(postedOfType(channel, 'release')).toHaveLength(1);
    expect(channel.closed).toBe(true);
  });

  it('should not broadcast a release on logout when already superseded', async () => {
    const { claim, release } = await loadSingleTab();
    claim();
    const [channel] = FakeBroadcastChannel.instances;
    receive(channel, { tabId: 'another-tab', type: 'claim' });

    release();

    expect(postedOfType(channel, 'release')).toHaveLength(0);
  });

  it('should hand off on pagehide when it is the active tab', async () => {
    const { claim } = await loadSingleTab();
    claim();
    const [channel] = FakeBroadcastChannel.instances;

    window.dispatchEvent(new Event('pagehide'));

    expect(postedOfType(channel, 'release')).toHaveLength(1);
  });

  it('should not hand off on pagehide when superseded', async () => {
    const { claim } = await loadSingleTab();
    claim();
    const [channel] = FakeBroadcastChannel.instances;
    receive(channel, { tabId: 'another-tab', type: 'claim' });

    window.dispatchEvent(new Event('pagehide'));

    expect(postedOfType(channel, 'release')).toHaveLength(0);
  });

  it('should not hand off on pagehide during its own reclaim reload', async () => {
    const { reclaim } = await loadSingleTab();
    reclaim();
    const [channel] = FakeBroadcastChannel.instances;

    window.dispatchEvent(new Event('pagehide'));

    expect(postedOfType(channel, 'release')).toHaveLength(0);
  });

  it('should be inert in the electron build', async () => {
    set(isPackaged, true);
    const { claim, isActiveTab, supported } = await loadSingleTab();

    claim();

    expect(supported).toBe(false);
    expect(FakeBroadcastChannel.instances).toHaveLength(0);
    expect(get(isActiveTab)).toBe(true);
  });

  it('should be unsupported when BroadcastChannel is unavailable', async () => {
    vi.stubGlobal('BroadcastChannel', undefined);
    const { claim, supported } = await loadSingleTab();

    claim();

    expect(supported).toBe(false);
    expect(FakeBroadcastChannel.instances).toHaveLength(0);
  });
});
