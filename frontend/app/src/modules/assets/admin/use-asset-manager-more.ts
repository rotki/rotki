import type { RuiIcons } from '@rotki/ui-library';
import type { ComputedRef } from 'vue';
import type { RouteName } from '@/types/router';
import { msg } from '@/message-key';

/** A tool under the More section of Manage Assets: its path, label and icon from its nav meta, and what it is for. */
export interface AssetManagerMoreTool {
  readonly description: string;
  readonly icon: RuiIcons;
  readonly path: string;
  readonly text: string;
}

const TOOLS = [
  { descriptionKey: msg.$t('asset_management.more.descriptions.cex_mapping'), name: '/asset-manager/more/cex-mapping/' },
  { descriptionKey: msg.$t('asset_management.more.descriptions.counterparty_mapping'), name: '/asset-manager/more/counterparty-mapping/' },
  { descriptionKey: msg.$t('asset_management.more.descriptions.newly_detected'), name: '/asset-manager/more/newly-detected/' },
  { descriptionKey: msg.$t('asset_management.more.descriptions.missing_mappings'), name: '/asset-manager/more/missing-mappings/' },
  { descriptionKey: msg.$t('asset_management.more.descriptions.solana_token_migration'), name: '/asset-manager/more/solana-token-migration/' },
] as const satisfies readonly { descriptionKey: string; name: RouteName }[];

interface UseAssetManagerMoreReturn {
  current: ComputedRef<AssetManagerMoreTool | undefined>;
  tools: ComputedRef<AssetManagerMoreTool[]>;
}

/**
 * The tools under the More section of Manage Assets, in one place for the overview's cards and the
 * breadcrumb's switcher, so the two always list the same tools in the same order. Label and icon
 * come from each route's nav meta; a route without one is left out rather than breaking the list.
 */
export function useAssetManagerMore(): UseAssetManagerMoreReturn {
  const { t } = useI18n({ useScope: 'global' });
  const router = useRouter();
  const route = useRoute();

  const tools = computed<AssetManagerMoreTool[]>(() => TOOLS.flatMap((tool) => {
    const nav = router.getRoutes().find(record => record.name === tool.name)?.meta.nav;
    if (!nav)
      return [];

    return [{
      description: t(tool.descriptionKey),
      icon: nav.icon,
      path: router.resolve({ name: tool.name }).path,
      text: t(nav.labelKey),
    }];
  }));

  const current = computed<AssetManagerMoreTool | undefined>(() => {
    const path = get(route).path;
    return get(tools).find(tool => path.startsWith(tool.path.replace(/\/$/, '')));
  });

  return { current, tools };
}
