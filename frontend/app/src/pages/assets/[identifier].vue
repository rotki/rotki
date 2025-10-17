<script setup lang="ts">
import type { AssetBalanceWithPrice } from '@rotki/common';
import type { RouteLocationRaw } from 'vue-router';
import { externalLinks } from '@shared/external-links';
import ManagedAssetIgnoringMore from '@/components/asset-manager/managed/ManagedAssetIgnoringMore.vue';
import AssetBalances from '@/components/AssetBalances.vue';
import AssetLocations from '@/components/assets/AssetLocations.vue';
import AssetValueRow from '@/components/assets/AssetValueRow.vue';
import AppImage from '@/components/common/AppImage.vue';
import AssetAmountAndValuePlaceholder from '@/components/graphs/AssetAmountAndValuePlaceholder.vue';
import AssetIcon from '@/components/helper/display/icons/AssetIcon.vue';
import ExternalLink from '@/components/helper/ExternalLink.vue';
import TablePageLayout from '@/components/layout/TablePageLayout.vue';
import { type AssetResolutionOptions, useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useSpamAsset } from '@/composables/assets/spam';
import { useAggregatedBalances } from '@/composables/balances/use-aggregated-balances';
import { useSupportedChains } from '@/composables/info/chains';
import { usePremium } from '@/composables/premium';
import HashLink from '@/modules/common/links/HashLink.vue';
import { AssetAmountAndValueOverTime } from '@/premium/premium';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { useWhitelistedAssetsStore } from '@/store/assets/whitelisted';
import { EVM_TOKEN } from '@/types/asset';
import { NoteLocation } from '@/types/notes';
import { getPublicServiceImagePath } from '@/utils/file';

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

const { t } = useI18n({ useScope: 'global' });
const router = useRouter();
const route = useRoute();

const { coingeckoAsset, cryptocompareAsset } = externalLinks;

const { ignoreAssetWithConfirmation, unignoreAsset, useIsAssetIgnored } = useIgnoredAssetsStore();
const { isAssetWhitelisted, unWhitelistAsset, whitelistAsset } = useWhitelistedAssetsStore();
const { markAssetsAsSpam, removeAssetFromSpamList } = useSpamAsset();
const { assetInfo, assetName, assetSymbol, refetchAssetInfo, tokenAddress } = useAssetInfoRetrieval();
const { getChain } = useSupportedChains();
const premium = usePremium();
const { balances } = useAggregatedBalances();

const aggregatedBalances = balances();

const isIgnored = useIsAssetIgnored(identifier);
const isWhitelisted = isAssetWhitelisted(identifier);

const isCollectionParent = computed<boolean>(() => {
  const currentRoute = get(route);
  const collectionParent = currentRoute.query.collectionParent;

  return !!collectionParent;
});

const assetRetrievalOption = computed<AssetResolutionOptions>(() => ({
  collectionParent: get(isCollectionParent),
}));

const name = assetName(identifier, assetRetrievalOption);
const symbol = assetSymbol(identifier, assetRetrievalOption);
const asset = assetInfo(identifier, assetRetrievalOption);
const address = tokenAddress(identifier);
const chain = computed(() => {
  const evmChain = get(asset)?.evmChain;
  if (evmChain)
    return getChain(evmChain);

  return undefined;
});
const isCustomAsset = computed(() => get(asset)?.isCustomAsset);

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

const collectionBalance = computed<AssetBalanceWithPrice[]>(() => {
  if (!get(isCollectionParent))
    return [];

  return get(aggregatedBalances).find(data => data.asset === get(identifier))?.breakdown || [];
});

const collectionAssetWithPrice = computed<string | undefined>(() => {
  const collectionBalanceVal = get(collectionBalance);

  const id = get(identifier);

  if (collectionBalanceVal.length === 0) {
    return id;
  }

  if (collectionBalanceVal.some(item => item.asset === id)) {
    return id;
  }

  return collectionBalanceVal[0].asset;
});

const isSpam = computed(() => get(asset)?.isSpam || false);

function goToEdit() {
  router.push(get(editRoute));
}

async function toggleSpam() {
  const id = get(identifier);
  if (get(isSpam))
    await removeAssetFromSpamList(id);
  else
    await markAssetsAsSpam([id]);

  refetchAssetInfo(id);
}

async function toggleIgnoreAsset() {
  const id = get(identifier);
  if (get(isIgnored)) {
    await unignoreAsset(id);
  }
  else {
    await ignoreAssetWithConfirmation(id, get(symbol) || get(name));
  }
}

async function toggleWhitelistAsset() {
  const id = get(identifier);
  if (get(isWhitelisted))
    await unWhitelistAsset(id);
  else
    await whitelistAsset(id);

  refetchAssetInfo(id);
}
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
            :location="chain"
            type="token"
            :text="address"
            display-mode="link"
            hide-text
            size="18"
            class="[&_a]:!p-2.5"
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
                    :src="getPublicServiceImagePath('coingecko.svg')"
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
                    :src="getPublicServiceImagePath('cryptocompare.svg')"
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
          <RuiIcon name="lu-pencil" />
        </RuiButton>

        <template v-if="!isCustomAsset">
          <div class="text-body-2 mr-4">
            {{ t('assets.action.ignore') }}
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
        </template>

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
      :price-asset="collectionAssetWithPrice"
      :collection-id="collectionId"
    />

    <AssetAmountAndValuePlaceholder v-else />

    <AssetLocations
      v-if="!isCollectionParent"
      :identifier="identifier"
    />

    <RuiCard v-else>
      <template #header>
        {{ t('assets.multi_chain_assets') }}
      </template>

      <AssetBalances
        :balances="collectionBalance"
        all-breakdown
        hide-breakdown
      />
    </RuiCard>
  </TablePageLayout>
</template>
