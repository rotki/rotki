import { createMock } from '@test/utils/create-mock';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useNodeAvatars } from './use-node-avatars';

const { ensNames, loads } = vi.hoisted(() => {
  const sources: string[] = [];
  return { ensNames: new Map<string, string>(), loads: sources };
});

vi.mock('@/modules/accounts/use-blockie', () => ({
  useBlockie: (): object => ({ getBlockie: (address: string): string => `blockie:${address}` }),
}));

vi.mock('@/modules/accounts/address-book/use-address-name-resolution', async () => {
  const { computed } = await import('vue');
  return {
    useAddressNameResolution: (): object => ({
      useEnsAvatarUrl: (address: string): object => computed<string | null>(() => {
        const ens = ensNames.get(address);
        return ens ? `/avatars/ens/${ens}` : null;
      }),
    }),
  };
});

/** An image that loads every source except ENS avatars of names starting with `missing`. */
class FakeImage {
  crossOrigin = '';
  source = '';
  private readonly listeners = new Map<string, () => void>();

  addEventListener(type: string, listener: () => void): void {
    this.listeners.set(type, listener);
  }

  get src(): string {
    return this.source;
  }

  set src(source: string) {
    this.source = source;
    loads.push(source);
    setTimeout(() => this.listeners.get(source.includes('/missing') ? 'error' : 'load')?.(), 0);
  }
}

let drawn = '';

describe('use node avatars', () => {
  beforeEach(() => {
    ensNames.clear();
    loads.length = 0;
    vi.stubGlobal('Image', FakeImage);
    vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(createMock<CanvasRenderingContext2D>({
      drawImage: vi.fn<(image: CanvasImageSource) => void>((image) => {
        drawn = String(Reflect.get(image, 'source'));
      }),
    }));
    vi.spyOn(HTMLCanvasElement.prototype, 'toDataURL').mockImplementation(() => `rounded:${drawn}`);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('should draw the ENS avatar when the address has one, and the blockie otherwise', async () => {
    ensNames.set('0xa', 'alice.eth');
    const avatars = useNodeAvatars(['0xa', '0xb'], 'white');
    await vi.waitFor(() => expect(get(avatars).size).toBe(2));

    expect(get(avatars).get('0xa')).toBe('rounded:/avatars/ens/alice.eth');
    expect(get(avatars).get('0xb')).toBe('rounded:blockie:0xb');
  });

  it('should fall back to the blockie when the ENS avatar fails, and not ask for it again', async () => {
    ensNames.set('0xc', 'missing.eth');
    const first = useNodeAvatars(['0xc'], 'white');
    await vi.waitFor(() => expect(get(first).get('0xc')).toBe('rounded:blockie:0xc'));

    const second = useNodeAvatars(['0xc'], 'black');
    await vi.waitFor(() => expect(get(second).get('0xc')).toBe('rounded:blockie:0xc'));

    expect(loads.filter(source => source.includes('missing.eth'))).toHaveLength(1);
  });
});
