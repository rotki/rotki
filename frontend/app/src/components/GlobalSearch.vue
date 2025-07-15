<script setup lang="ts">
import type { AssetBalanceWithPrice, BigNumber } from '@rotki/common';
import type { RuiIcons } from '@rotki/ui-library';
import type { RouteLocationRaw } from 'vue-router';
import type { Exchange } from '@/types/exchanges';
import type { TradeLocationData } from '@/types/history/trade/location';
import { startPromise } from '@shared/utils';
import AppImage from '@/components/common/AppImage.vue';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import AssetIcon from '@/components/helper/display/icons/AssetIcon.vue';
import LocationIcon from '@/components/history/LocationIcon.vue';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useAggregatedBalances } from '@/composables/balances/use-aggregated-balances';
import { useInterop } from '@/composables/electron-interop';
import { useLocations } from '@/composables/locations';
import { useAppRoutes } from '@/router/routes';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useSessionSettingsStore } from '@/store/settings/session';

withDefaults(
  defineProps<{
    isMini?: boolean;
  }>(),
  {
    isMini: false,
  },
);

interface SearchItem {
  value: number;
  text?: string;
  texts?: string[];
  asset?: string;
  location?: TradeLocationData;
  price?: BigNumber;
  total?: BigNumber;
  icon?: RuiIcons;
  image?: string;
  route?: RouteLocationRaw;
  action?: () => void;
  matchedPoints?: number;
}

type SearchItemWithoutValue = Omit<SearchItem, 'value'>;

const { t } = useI18n({ useScope: 'global' });
const { appRoutes } = useAppRoutes();
const Routes = get(appRoutes);
const open = ref<boolean>(false);
const isMac = ref<boolean>(false);

const input = ref<any>(null);
const selected = ref<number>();
const search = ref<string>('');
const loading = ref(false);
const visibleItems = ref<SearchItem[]>([]);

const key = '/';

const router = useRouter();

const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
const { connectedExchanges } = storeToRefs(useSessionSettingsStore());
const { balances, balancesByLocation } = useAggregatedBalances();
const { getLocationData } = useLocations();
const { assetSearch } = useAssetInfoRetrieval();

function getItemText(item: SearchItemWithoutValue): string {
  const text = item.texts ? item.texts.join(' ') : item.text;
  return (
    text
      ?.replace(/[^\s\w]/g, ' ')
      .replace(/\s+/g, ' ')
      .trim() ?? ''
  );
}

function filterItems(items: SearchItemWithoutValue[], keyword: string): SearchItemWithoutValue[] {
  const splitKeyword = keyword.split(' ');
  return items.filter((item) => {
    let matchedPoints = 0;
    for (const word of splitKeyword) {
      const indexOf = getItemText(item).toLowerCase().indexOf(word);
      if (indexOf > -1) {
        matchedPoints++;
        if (indexOf === 0)
          matchedPoints += 0.5;
      }
    }
    item.matchedPoints = matchedPoints;
    return matchedPoints > 0;
  });
}

function getRoutes(keyword: string): SearchItemWithoutValue[] {
  const routeItems: SearchItemWithoutValue[] = [
    { ...Routes.DASHBOARD },
    {
      ...Routes.ACCOUNTS_EVM,
      texts: [Routes.ACCOUNTS.text, Routes.ACCOUNTS_EVM.text],
    },
    {
      ...Routes.ACCOUNTS_BITCOIN,
      texts: [Routes.ACCOUNTS.text, Routes.ACCOUNTS_BITCOIN.text],
    },
    {
      ...Routes.ACCOUNTS_SUBSTRATE,
      texts: [Routes.ACCOUNTS.text, Routes.ACCOUNTS_SUBSTRATE.text],
    },
    {
      ...Routes.BALANCES_BLOCKCHAIN,
      texts: [Routes.BALANCES.text, Routes.BALANCES_BLOCKCHAIN.text],
    },
    {
      ...Routes.BALANCES_EXCHANGE,
      texts: [Routes.BALANCES.text, Routes.BALANCES_EXCHANGE.text],
    },
    {
      ...Routes.BALANCES_MANUAL,
      texts: [Routes.BALANCES.text, Routes.BALANCES_MANUAL.text],
    },
    {
      ...Routes.BALANCES_NON_FUNGIBLE,
      texts: [Routes.BALANCES.text, Routes.BALANCES_NON_FUNGIBLE.text],
    },
    {
      ...Routes.ONCHAIN_SEND,
      texts: [Routes.ONCHAIN.text, Routes.ONCHAIN_SEND.text],
    },
    { ...Routes.NFTS },
    { ...Routes.HISTORY },
    { ...Routes.AIRDROPS },
    { ...Routes.STATISTICS },
    { ...Routes.STAKING },
    { ...Routes.PROFIT_LOSS_REPORTS },
    { ...Routes.TAG_MANAGER },
    {
      ...Routes.ASSET_MANAGER_MANAGED,
      texts: [Routes.ASSET_MANAGER.text, Routes.ASSET_MANAGER_MANAGED.text],
    },
    {
      ...Routes.ASSET_MANAGER_CUSTOM,
      texts: [Routes.ASSET_MANAGER.text, Routes.ASSET_MANAGER_CUSTOM.text],
    },
    {
      ...Routes.ASSET_MANAGER_CEX_MAPPING,
      texts: [Routes.ASSET_MANAGER.text, Routes.ASSET_MANAGER_CEX_MAPPING.text],
    },
    {
      ...Routes.ASSET_MANAGER_NEWLY_DETECTED,
      texts: [Routes.ASSET_MANAGER.text, Routes.ASSET_MANAGER_NEWLY_DETECTED.text],
    },
    {
      ...Routes.PRICE_MANAGER_LATEST,
      texts: [Routes.PRICE_MANAGER.text, Routes.PRICE_MANAGER_LATEST.text],
    },
    {
      ...Routes.PRICE_MANAGER_HISTORIC,
      texts: [Routes.PRICE_MANAGER.text, Routes.PRICE_MANAGER_HISTORIC.text],
    },
    { ...Routes.ADDRESS_BOOK_MANAGER },
    {
      ...Routes.API_KEYS_ROTKI_PREMIUM,
      texts: [Routes.API_KEYS.text, Routes.API_KEYS_ROTKI_PREMIUM.text],
    },
    {
      ...Routes.API_KEYS_EXCHANGES,
      texts: [Routes.API_KEYS.text, Routes.API_KEYS_EXCHANGES.text],
    },
    {
      ...Routes.API_KEYS_EXTERNAL_SERVICES,
      texts: [Routes.API_KEYS.text, Routes.API_KEYS_EXTERNAL_SERVICES.text],
    },
    { ...Routes.IMPORT },
    {
      ...Routes.SETTINGS_ACCOUNT,
      texts: [Routes.SETTINGS.text, Routes.SETTINGS_ACCOUNT.text],
    },
    {
      ...Routes.SETTINGS_GENERAL,
      texts: [Routes.SETTINGS.text, Routes.SETTINGS_GENERAL.text],
    },
    {
      ...Routes.SETTINGS_DATABASE,
      texts: [Routes.SETTINGS.text, Routes.SETTINGS_DATABASE.text],
    },
    {
      ...Routes.SETTINGS_ACCOUNTING,
      texts: [Routes.SETTINGS.text, Routes.SETTINGS_ACCOUNTING.text],
    },
    {
      ...Routes.SETTINGS_ORACLE,
      texts: [Routes.SETTINGS.text, Routes.SETTINGS_ORACLE.text],
    },
    {
      ...Routes.SETTINGS_RPC,
      texts: [Routes.SETTINGS.text, Routes.SETTINGS_RPC.text],
    },
    {
      ...Routes.SETTINGS_MODULES,
      texts: [Routes.SETTINGS.text, Routes.SETTINGS_MODULES.text],
    },
    {
      ...Routes.SETTINGS_INTERFACE,
      texts: [Routes.SETTINGS.text, Routes.SETTINGS_INTERFACE.text],
    },
    {
      ...Routes.CALENDAR,
    },
  ];

  return filterItems(routeItems, keyword);
}

function getExchanges(keyword: string): SearchItemWithoutValue[] {
  const exchanges = get(connectedExchanges);
  const exchangeItems: SearchItemWithoutValue[] = exchanges.map((exchange: Exchange) => {
    const identifier = exchange.location;
    const name = exchange.name;

    return {
      location: getLocationData(identifier) ?? undefined,
      route: `${Routes.BALANCES_EXCHANGE.route}/${identifier}`,
      texts: [Routes.BALANCES.text, Routes.BALANCES_EXCHANGE.text, name],
    };
  });

  return filterItems(exchangeItems, keyword);
}

function getActions(keyword: string): SearchItemWithoutValue[] {
  const actionItems: SearchItemWithoutValue[] = [
    {
      route: `${Routes.API_KEYS_EXCHANGES.route}?add=true`,
      text: t('exchange_settings.dialog.add.title'),
    },
    {
      route: `${Routes.ACCOUNTS_EVM.route}?add=true`,
      text: t('blockchain_balances.form_dialog.add_title'),
    },
    {
      route: `${Routes.BALANCES_MANUAL.route}?add=true`,
      text: t('manual_balances.dialog.add.title'),
    },
    {
      route: `${Routes.ASSET_MANAGER.route}?add=true`,
      text: t('asset_management.add_title'),
    },
    {
      route: `${Routes.PRICE_MANAGER_LATEST.route}?add=true`,
      text: t('price_management.latest.add_title'),
    },
    {
      route: `${Routes.PRICE_MANAGER_HISTORIC.route}?add=true`,
      text: t('price_management.historic.add_title'),
    },
    {
      route: `${Routes.ASSET_MANAGER_CEX_MAPPING.route}?add=true`,
      text: t('asset_management.cex_mapping.add_title'),
    },
    {
      route: `${Routes.TAG_MANAGER.route}?add=true`,
      text: t('tag_manager.create_tag.title'),
    },
  ].map(item => ({ ...item, icon: 'lu-circle-plus' }));

  return filterItems(actionItems, keyword);
}

async function getAssets(keyword: string): Promise<SearchItemWithoutValue[]> {
  const matches = await assetSearch({
    limit: 5,
    value: keyword,
  });
  const assetBalances = get(balances()) as AssetBalanceWithPrice[];
  const map: Record<string, string> = {};
  for (const match of matches) map[match.identifier] = match.symbol ?? match.name ?? '';

  const ids = matches.map(({ identifier }) => identifier);

  return assetBalances
    .filter(balance => ids.includes(balance.asset))
    .map((balance) => {
      const price = balance.usdPrice.gt(0) ? balance.usdPrice : undefined;
      const asset = balance.asset;

      return {
        asset,
        price,
        route: {
          name: '/assets/[identifier]',
          params: {
            identifier: asset,
          },
        },
        texts: [t('common.asset'), map[asset] ?? ''],
      };
    });
}

function* transformLocations(): IterableIterator<SearchItemWithoutValue> {
  const locationBalances = get(balancesByLocation);

  for (const identifier in locationBalances) {
    const location = getLocationData(identifier);
    if (!location)
      continue;

    const total = locationBalances[identifier];
    yield {
      location,
      route: {
        name: '/locations/[identifier]',
        params: {
          identifier: encodeURIComponent(location.identifier),
        },
      },
      texts: [t('common.location'), location.name],
      total,
    } satisfies SearchItemWithoutValue;
  }
}

function getLocations(keyword: string) {
  return filterItems([...transformLocations()], keyword);
}

watchDebounced(
  search,
  async (keyword) => {
    if (!keyword) {
      set(visibleItems, []);
      return;
    }

    const search = keyword.toLocaleLowerCase().trim();

    const staticData = [
      ...getRoutes(search),
      ...getExchanges(search),
      ...getActions(search),
      ...getLocations(search),
    ].sort((a, b) => (b.matchedPoints ?? 0) - (a.matchedPoints ?? 0));

    set(
      visibleItems,
      [...staticData, ...(await getAssets(search))].map((item, index) => ({
        ...item,
        text: getItemText(item),
        value: index,
      })),
    );

    set(loading, false);
  },
  {
    debounce: 800,
  },
);

watch(search, (search) => {
  set(loading, !!search);
});

watch(open, (open) => {
  nextTick(() => {
    if (open) {
      setTimeout(() => {
        get(input)?.focus?.();
      }, 100);
    }
    set(selected, undefined);
    set(search, '');
  });
});

function change(index?: number) {
  if (!isDefined(index))
    return;

  const item: SearchItem = get(visibleItems)[index];
  if (item) {
    if (item.route && get(router.currentRoute).fullPath !== item.route)
      startPromise(router.push(item.route));

    item?.action?.();
    set(open, false);
  }
}

const interop = useInterop();
onBeforeMount(async () => {
  set(isMac, await interop.isMac());

  window.addEventListener('keydown', (event) => {
    // Mac use Command, Others use Control
    if (((get(isMac) && event.metaKey) || (!get(isMac) && event.ctrlKey)) && event.key === key)
      set(open, true);
  });
});
</script>

<template>
  <RuiDialog
    v-model="open"
    max-width="800"
    content-class="mt-[16rem] !top-0 pb-2"
  >
    <template #activator="{ attrs }">
      <div
        v-if="!isMini"
        class="px-3 pt-2 pb-4"
      >
        <RuiTextField
          model-value=""
          hide-details
          dense
          :label="t('common.actions.search')"
          variant="outlined"
          readonly
          class="opacity-60 [&>div:first-child]:bg-rui-grey-100 [&>div:first-child]:dark:bg-rui-grey-800 [&_fieldset]:!rounded-lg [&_fieldset]:!opacity-50"
          color="primary"
          v-bind="attrs"
        >
          <template #prepend>
            <RuiIcon
              name="lu-search"
              size="18"
            />
          </template>
          <template #append>
            <RuiIcon
              name="lu-command"
              size="14"
            />
            {{ key }}
          </template>
        </RuiTextField>
      </div>
      <RuiButton
        v-else
        variant="text"
        class=" p-2 w-full mb-4 border border-rui-grey-200 dark:border-rui-grey-700 !bg-rui-grey-100 hover:!bg-rui-grey-200 dark:!bg-rui-grey-800 hover:dark:!bg-rui-grey-700 rounded-lg"
        v-bind="attrs"
      >
        <RuiIcon
          name="lu-search"
          class="opacity-40"
          size="20"
        />
      </RuiButton>
    </template>
    <RuiCard
      variant="flat"
      no-padding
      rounded="sm"
      content-class="overflow-hidden"
    >
      <RuiAutoComplete
        ref="input"
        v-model="selected"
        v-model:search-input="search"
        no-filter
        :no-data-text="t('global_search.no_actions')"
        hide-details
        :loading="loading"
        :item-height="50"
        :options="visibleItems"
        text-attr="text"
        key-attr="value"
        label=""
        auto-select-first
        :placeholder="t('global_search.search_placeholder')"
        @update:model-value="change($event)"
      >
        <template #selection>
          <span />
        </template>
        <template #item="{ item }">
          <div class="flex items-center text-body-2 w-full">
            <AssetIcon
              v-if="item.asset"
              class="-my-1"
              size="30px"
              :identifier="item.asset"
            />
            <template v-else>
              <LocationIcon
                v-if="item.location"
                icon
                size="26px"
                :item="item.location.identifier"
              />
              <AppImage
                v-else-if="item.image"
                class="icon-bg"
                :src="item.image"
                contain
                size="26px"
              />
              <RuiIcon
                v-else-if="item.icon"
                :name="item.icon"
                size="26px"
              />
            </template>
            <div class="ml-3 flex items-center">
              <template v-if="item.texts">
                <div
                  v-for="(text, index) in item.texts"
                  :key="text + index"
                  class="flex items-center"
                >
                  <div v-if="index === item.texts.length - 1">
                    {{ text }}
                  </div>
                  <div
                    v-else
                    class="flex items-center text-rui-text-secondary"
                  >
                    {{ text }}
                    <RuiIcon
                      class="d-inline mx-2"
                      size="16"
                      name="lu-chevron-right"
                    />
                  </div>
                </div>
              </template>
              <template v-else>
                {{ item.text }}
              </template>
            </div>
            <div class="grow" />
            <div
              v-if="item.price"
              class="text-right -my-6"
            >
              <div class="text-caption">
                {{ t('common.price') }}:
              </div>
              <AmountDisplay
                class="font-bold"
                :fiat-currency="currencySymbol"
                :value="item.price"
              />
            </div>
            <div
              v-if="item.total"
              class="text-right -my-4"
            >
              <div class="text-caption">
                {{ t('common.total') }}:
              </div>
              <AmountDisplay
                class="font-bold"
                :fiat-currency="currencySymbol"
                :value="item.total"
              />
            </div>
          </div>
        </template>
      </RuiAutoComplete>
    </RuiCard>
  </RuiDialog>
</template>
