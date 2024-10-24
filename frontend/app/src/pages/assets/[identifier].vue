<script setup lang="ts">
import { AssetAmountAndValueOverTime } from '@/premium/premium';
import { EVM_TOKEN } from '@/types/asset';
import { NoteLocation } from '@/types/notes';
import type { RouteLocationRaw } from 'vue-router';
import type { AssetBalanceWithBreakdown } from '@/types/balances';

definePage({
  meta: {
    canNavigateBack: true,
    noteLocation: NoteLocation.ASSETS,
  },
  props: true,
});

defineOptions({
  name: 'AssetBreakdown',
});

const props = defineProps<{
  identifier: string;
}>();

const { identifier } = toRefs(props);
const { isAssetIgnored, ignoreAsset, unignoreAsset } = useIgnoredAssetsStore();
const { isAssetWhitelisted, whitelistAsset, unWhitelistAsset } = useWhitelistedAssetsStore();
const { markAssetsAsSpam, removeAssetFromSpamList } = useSpamAsset();
const { assetName, assetSymbol, assetInfo, tokenAddress, refetchAssetInfo } = useAssetInfoRetrieval();
const { getChain } = useSupportedChains();

const isIgnored = isAssetIgnored(identifier);
const isWhitelisted = isAssetWhitelisted(identifier);

async function toggleIgnoreAsset() {
  const id = get(identifier);
  if (get(isIgnored))
    await unignoreAsset(id);
  else
    await ignoreAsset(id);
}

async function toggleWhitelistAsset() {
  const id = get(identifier);
  if (get(isWhitelisted))
    await unWhitelistAsset(id);
  else
    await whitelistAsset(id);

  refetchAssetInfo(id);
}
const premium = usePremium();

const name = assetName(identifier);
const symbol = assetSymbol(identifier);
const asset = assetInfo(identifier);
const address = tokenAddress(identifier);
const chain = computed(() => {
  const evmChain = get(asset)?.evmChain;
  if (evmChain)
    return getChain(evmChain);

  return undefined;
});
const isCustomAsset = computed(() => get(asset)?.isCustomAsset);

const { t } = useI18n();

const route = useRoute();
const router = useRouter();

const isCollectionParent = computed<boolean>(() => {
  const currentRoute = get(route);
  const collectionParent = currentRoute.query.collectionParent;

  return !!collectionParent;
});

const collectionId = computed<number | undefined>(() => {
  if (!get(isCollectionParent))
    return undefined;

  const collectionId = get(asset)?.collectionId;
  return (collectionId && parseInt(collectionId)) || undefined;
});

const editRoute = computed<RouteLocationRaw>(() => ({
  path: get(isCustomAsset) ? '/asset-manager/custom' : '/asset-manager/managed',
  query: {
    id: get(identifier),
  },
}));

const { balances } = useAggregatedBalances();
const collectionBalance = computed<AssetBalanceWithBreakdown[]>(() => {
  if (!get(isCollectionParent))
    return [];

  return get(balances()).find(data => data.asset === get(identifier))?.breakdown || [];
});

function goToEdit() {
  router.push(get(editRoute));
}

const isSpam = computed(() => get(asset)?.isSpam || false);

async function toggleSpam() {
  const id = get(identifier);
  if (get(isSpam))
    await removeAssetFromSpamList(id);
  else
    await markAssetsAsSpam([id]);

  refetchAssetInfo(id);
}

const {
  coingeckoAsset,
  cryptocompareAsset,
} = externalLinks;
</script>

<template>
  <TablePageLayout
    class="p-4"
    hide-header
  >
    <div class="flex flex-wrap justify-between w-full gap-4">
      <div class="flex gap-4 items-center">
        <AssetIcon
          :identifier="identifier"
          size="48px"
          :show-chain="!isCollectionParent"
        />

        <div
          v-if="!isCustomAsset"
          class="flex flex-col"
        >
          <span class="text-h5 font-medium">{{ symbol }}</span>
          <span class="text-body-2 text-rui-text-secondary">
            {{ name }}
          </span>
        </div>

        <div
          v-else
          class="flex flex-col"
        >
          <span class="text-h5 font-medium">{{ name }}</span>
          <span class="text-body-2 text-rui-text-secondary">
            {{ asset?.customAssetType }}
          </span>
        </div>

        <div class="flex items-center gap-2 ml-4">
          <HashLink
            v-if="address"
            :chain="chain"
            type="address"
            :text="address"
            link-only
            size="18"
            class="[&_a]:!p-2.5"
            :show-icon="false"
          />

          <template
            v-if="asset"
          >
            <ExternalLink
              v-if="asset.coingecko"
              custom
              :url="coingeckoAsset.replace('$symbol', asset.coingecko)"
            >
              <RuiButton
                size="sm"
                icon
              >
                <template #prepend>
                  <AppImage
                    size="30px"
                    src="./assets/images/oracles/coingecko.svg"
                  />
                </template>
              </RuiButton>
            </ExternalLink>
            <ExternalLink
              v-if="asset.cryptocompare"
              custom
              :url="cryptocompareAsset.replace('$symbol', asset.cryptocompare)"
            >
              <RuiButton
                size="sm"
                icon
              >
                <template #prepend>
                  <AppImage
                    size="30px"
                    src="./assets/images/oracles/cryptocompare.png"
                  />
                </template>
              </RuiButton>
            </ExternalLink>
          </template>
        </div>
      </div>
      <div class="flex items-center gap-2">
        <RuiButton
          v-if="!isCollectionParent"
          icon
          variant="text"
          @click="goToEdit()"
        >
          <RuiIcon name="pencil-line" />
        </RuiButton>

        <div class="text-body-2 mr-4">
          {{ t('assets.ignore') }}
        </div>

        <RuiTooltip
          :popper="{ placement: 'top' }"
          :open-delay="400"
          tooltip-class="max-w-[10rem]"
          :disabled="!isSpam"
        >
          <template #activator>
            <RuiSwitch
              color="primary"
              hide-details
              :disabled="isSpam"
              :model-value="isIgnored"
              @update:model-value="toggleIgnoreAsset()"
            />
          </template>
          {{ t('ignore.spam.hint') }}
        </RuiTooltip>

        <ManagedAssetIgnoringMore
          v-if="asset?.assetType === EVM_TOKEN"
          :identifier="identifier"
          :is-spam="isSpam"
          @toggle-whitelist="toggleWhitelistAsset()"
          @toggle-spam="toggleSpam()"
        />
      </div>
    </div>

    <AssetValueRow
      :is-collection-parent="isCollectionParent"
      :identifier="identifier"
    />

    <AssetAmountAndValueOverTime
      v-if="premium"
      :asset="identifier"
      :collection-id="collectionId"
    />

    <AssetLocations
      v-if="!isCollectionParent"
      :identifier="identifier"
    />

    <RuiCard v-else>
      <template #header>
        {{ t('assets.multi_chain_assets') }}
      </template>

      <AssetBalances :balances="collectionBalance" />
    </RuiCard>
  </TablePageLayout>
</template>
