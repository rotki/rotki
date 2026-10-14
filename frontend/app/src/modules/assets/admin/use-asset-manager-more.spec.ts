import { beforeEach, describe, expect, it, vi } from 'vitest';
import { computed, type Ref, ref } from 'vue';
import { useAssetManagerMore } from '@/modules/assets/admin/use-asset-manager-more';

interface FakeRecord {
  name: string;
  meta: { nav?: { icon: string; labelKey: string } };
}

const routePath = ref<string>('/asset-manager/more');
const records = ref<FakeRecord[]>([]);

vi.mock('vue-router', () => ({
  useRoute: (): Ref<{ path: string }> => computed(() => ({ path: get(routePath) })),
  useRouter: (): Record<string, unknown> => ({
    getRoutes: (): FakeRecord[] => get(records),
    resolve: ({ name }: { name: string }): { path: string } => ({ path: name }),
  }),
}));

function record(name: string, icon: string, labelKey: string): FakeRecord {
  return { meta: { nav: { icon, labelKey } }, name };
}

describe('useAssetManagerMore', () => {
  beforeEach(() => {
    set(routePath, '/asset-manager/more');
    // Out of order on purpose: the list follows the tool order, not the router's.
    set(records, [
      record('/asset-manager/more/solana-token-migration/', 'lu-coins', 'navigation_menu.manage_assets_sub.solana_token_migration'),
      record('/asset-manager/more/missing-mappings/', 'lu-scroll', 'navigation_menu.manage_assets_sub.missing_mappings'),
      record('/asset-manager/more/newly-detected/', 'lu-list-collapse', 'navigation_menu.manage_assets_sub.newly_detected'),
      record('/asset-manager/more/counterparty-mapping/', 'lu-list-todo', 'navigation_menu.manage_assets_sub.counterparty_mapping'),
      record('/asset-manager/more/cex-mapping/', 'lu-scroll-text', 'navigation_menu.manage_assets_sub.cex_mapping'),
      record('/asset-manager/managed/', 'lu-manage-assets', 'navigation_menu.manage_assets_sub.assets'),
    ]);
  });

  it('should list the five tools in a fixed order, with path and icon from their routes', () => {
    const { tools } = useAssetManagerMore();

    expect(get(tools).map(tool => tool.path)).toEqual([
      '/asset-manager/more/cex-mapping/',
      '/asset-manager/more/counterparty-mapping/',
      '/asset-manager/more/newly-detected/',
      '/asset-manager/more/missing-mappings/',
      '/asset-manager/more/solana-token-migration/',
    ]);
    expect(get(tools)[0].icon).toBe('lu-scroll-text');
  });

  it('should take the label from the nav meta and the description from the tool', () => {
    const { tools } = useAssetManagerMore();

    expect(get(tools)[0]).toMatchObject({
      description: 'asset_management.more.descriptions.cex_mapping',
      text: 'navigation_menu.manage_assets_sub.cex_mapping',
    });
  });

  it('should leave out a tool whose route has no nav meta', () => {
    set(records, get(records).map(item => (item.name === '/asset-manager/more/newly-detected/' ? { ...item, meta: {} } : item)));
    const { tools } = useAssetManagerMore();

    expect(get(tools)).toHaveLength(4);
    expect(get(tools).map(tool => tool.path)).not.toContain('/asset-manager/more/newly-detected/');
  });

  it('should find no current tool on the overview', () => {
    const { current } = useAssetManagerMore();

    expect(get(current)).toBeUndefined();
  });

  it('should find the current tool from the route, including its sub-pages', () => {
    const { current } = useAssetManagerMore();

    set(routePath, '/asset-manager/more/missing-mappings');
    expect(get(current)?.path).toBe('/asset-manager/more/missing-mappings/');

    set(routePath, '/asset-manager/more/cex-mapping/binance');
    expect(get(current)?.path).toBe('/asset-manager/more/cex-mapping/');
  });
});
