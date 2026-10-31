import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import { startPromise } from '@shared/utils';
import { useAddressNameResolution } from '@/modules/accounts/address-book/use-address-name-resolution';
import { useBlockie } from '@/modules/accounts/use-blockie';

/** Drawn at twice the largest node size, so avatars stay sharp on high-density screens. */
const AVATAR_PIXELS = 96;

const RING_PIXELS = 6;

const rounded = new Map<string, string>();

/**
 * ENS avatar URLs that failed to load, so a redraw does not ask the backend for them again. The URL
 * carries the avatar refresh timestamp, so a refresh, or the next mount, tries again.
 */
const missingEnsAvatars = new Set<string>();

async function loadImage(source: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.crossOrigin = 'anonymous';
    image.addEventListener('load', () => resolve(image));
    image.addEventListener('error', reject);
    image.src = source;
  });
}

/** Clips a square image to a circle with a ring, matching the round avatars in the side list. */
async function roundAvatar(source: string, ring: string): Promise<string | undefined> {
  const image = await loadImage(source);
  const canvas = document.createElement('canvas');
  canvas.width = AVATAR_PIXELS;
  canvas.height = AVATAR_PIXELS;
  const context = canvas.getContext('2d');
  if (!context)
    return undefined;
  const center = AVATAR_PIXELS / 2;
  context.beginPath();
  context.arc(center, center, center, 0, Math.PI * 2);
  context.fillStyle = ring;
  context.fill();
  context.save();
  context.beginPath();
  context.arc(center, center, center - RING_PIXELS, 0, Math.PI * 2);
  context.clip();
  context.imageSmoothingEnabled = false;
  context.drawImage(image, RING_PIXELS, RING_PIXELS, AVATAR_PIXELS - RING_PIXELS * 2, AVATAR_PIXELS - RING_PIXELS * 2);
  context.restore();
  return canvas.toDataURL();
}

/**
 * Round avatars for the graph's addresses, as data URLs ECharts can draw as node symbols: the ENS
 * avatar when the address has an ENS name and its image loads, the blockie otherwise.
 *
 * @remarks
 * Images load asynchronously, so the map fills in after the first render and the chart falls back to
 * a plain circle until then. Pass the address as displayed (scrambled when scrambling is on): a
 * scrambled address has no ENS name, so neither its avatar nor its blockie reveals the real one. The
 * `ring` color separates an avatar from the edges running underneath it, so it should match the
 * chart surface.
 */
export function useNodeAvatars(addresses: MaybeRefOrGetter<readonly string[]>, ring: MaybeRefOrGetter<string>): Readonly<Ref<ReadonlyMap<string, string>>> {
  const { getBlockie } = useBlockie();
  const { useEnsAvatarUrl } = useAddressNameResolution();
  const ensUrls = new Map<string, ComputedRef<string | null>>();
  const avatars = shallowRef<ReadonlyMap<string, string>>(new Map());
  let latest = 0;

  /** The same timestamped URL `EnsAvatar` loads, so both refresh together; `null` without an ENS name. */
  function ensUrlOf(address: string): string | null {
    let url = ensUrls.get(address);
    if (!url) {
      url = useEnsAvatarUrl(address);
      ensUrls.set(address, url);
    }
    return get(url);
  }

  /** The ENS avatar, rounded; `undefined` when there is none or it already failed to load. */
  async function ensAvatar(url: string | null, ringColor: string): Promise<string | undefined> {
    if (!url || missingEnsAvatars.has(url))
      return undefined;
    const avatar = await roundAvatar(url, ringColor).catch(() => undefined);
    if (!avatar)
      missingEnsAvatars.add(url);
    return avatar;
  }

  async function blockieAvatar(address: string, ringColor: string): Promise<string | undefined> {
    const blockie = getBlockie(address);
    return blockie ? roundAvatar(blockie, ringColor).catch(() => undefined) : undefined;
  }

  async function avatarOf(address: string, ringColor: string): Promise<string | undefined> {
    const url = ensUrlOf(address);
    const key = `${ringColor}\u0000${url ?? address}`;
    const cached = rounded.get(key);
    if (cached)
      return cached;
    const avatar = await ensAvatar(url, ringColor) ?? await blockieAvatar(address, ringColor);
    if (avatar)
      rounded.set(key, avatar);
    return avatar;
  }

  async function draw(list: readonly string[], ringColor: string): Promise<void> {
    const request = ++latest;
    const entries = await Promise.all(list.map(async (address): Promise<[string, string | undefined]> => [address, await avatarOf(address, ringColor)]));
    if (request !== latest)
      return;
    set(avatars, new Map(entries.filter((entry): entry is [string, string] => entry[1] !== undefined)));
  }

  /**
   * One string for everything the avatars depend on, so an ENS store write that changes no URL does
   * not redraw them and rebuild the chart.
   */
  const drawKey = computed<string>(() => {
    const list = toValue(addresses);
    const current = new Set(list);
    for (const address of ensUrls.keys()) {
      if (!current.has(address))
        ensUrls.delete(address);
    }
    return [toValue(ring), ...list.map(address => `${address}=${ensUrlOf(address) ?? ''}`)].join('\u0000');
  });

  watch(drawKey, () => {
    startPromise(draw(toValue(addresses), toValue(ring)));
  }, { immediate: true });

  return readonly(avatars);
}
