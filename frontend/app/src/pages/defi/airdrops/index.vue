<script setup lang="ts">
import { type GeneralAccount } from '@rotki/common/lib/account';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { type Ref } from 'vue';
import { type DataTableHeader } from '@/types/vuetify';
import {
  AIRDROP_1INCH,
  AIRDROP_CONVEX,
  AIRDROP_CORNICHON,
  AIRDROP_COW_GNOSIS,
  AIRDROP_COW_MAINNET,
  AIRDROP_CURVE,
  AIRDROP_DIVA,
  AIRDROP_ENS,
  AIRDROP_FURUCOMBO,
  AIRDROP_GRAIN,
  AIRDROP_LIDO,
  AIRDROP_PARASWAP,
  AIRDROP_POAP,
  AIRDROP_SADDLE,
  AIRDROP_SHAPESHIFT,
  AIRDROP_TORNADO,
  AIRDROP_UNISWAP,
  type Airdrop,
  type AirdropType
} from '@/types/airdrops';
import { Section } from '@/types/status';

interface AirdropSource {
  readonly icon: string;
  readonly name: string;
}

type AirdropSources = {
  readonly [source in AirdropType]: AirdropSource;
};

const { t } = useI18n();

const expanded: Ref<Airdrop[]> = ref([]);
const selectedAccounts = ref<GeneralAccount[]>([]);
const statusFilters = ref<{ text: string; value: boolean }[]>([
  { text: t('common.unclaimed'), value: false },
  { text: t('common.claimed'), value: true }
]);
const status = ref(false);
const section = Section.DEFI_AIRDROPS;
const ETH = Blockchain.ETH;
const sources: AirdropSources = {
  [AIRDROP_UNISWAP]: {
    icon: './assets/images/protocols/uniswap.svg',
    name: 'Uniswap'
  },
  [AIRDROP_1INCH]: {
    icon: './assets/images/protocols/1inch.svg',
    name: '1inch'
  },
  [AIRDROP_TORNADO]: {
    icon: './assets/images/protocols/tornado.svg',
    name: 'Tornado Cash'
  },
  [AIRDROP_CORNICHON]: {
    icon: './assets/images/protocols/cornichon.svg',
    name: 'Cornichon'
  },
  [AIRDROP_GRAIN]: {
    icon: './assets/images/protocols/grain.png',
    name: 'Grain'
  },
  [AIRDROP_LIDO]: {
    icon: './assets/images/protocols/lido.svg',
    name: 'Lido'
  },
  [AIRDROP_FURUCOMBO]: {
    icon: './assets/images/protocols/furucombo.png',
    name: 'Furucombo'
  },
  [AIRDROP_CURVE]: {
    icon: './assets/images/protocols/curve.png',
    name: 'Curve Finance'
  },
  [AIRDROP_POAP]: {
    icon: './assets/images/protocols/poap.svg',
    name: 'POAP Delivery'
  },
  [AIRDROP_CONVEX]: {
    icon: './assets/images/protocols/convex.jpeg',
    name: 'Convex'
  },
  [AIRDROP_SHAPESHIFT]: {
    icon: './assets/images/protocols/shapeshift.svg',
    name: 'ShapeShift'
  },
  [AIRDROP_ENS]: {
    icon: './assets/images/protocols/ens.svg',
    name: 'ENS'
  },
  [AIRDROP_PARASWAP]: {
    icon: './assets/images/protocols/paraswap.svg',
    name: 'ParaSwap'
  },
  [AIRDROP_SADDLE]: {
    icon: './assets/images/protocols/saddle-finance.svg',
    name: 'SaddleFinance'
  },
  [AIRDROP_COW_MAINNET]: {
    icon: './assets/images/protocols/cow.svg',
    name: 'COW (ethereum)'
  },
  [AIRDROP_COW_GNOSIS]: {
    icon: './assets/images/protocols/cow.svg',
    name: 'COW (gnosis chain)'
  },
  [AIRDROP_DIVA]: {
    icon: './assets/images/protocols/diva.svg',
    name: 'DIVA'
  }
};

const css = useCssModule();
const airdropStore = useAirdropStore();
const { airdropAddresses } = storeToRefs(airdropStore);
const { isPackaged, navigate } = useInterop();
const { isLoading, shouldShowLoadingScreen } = useStatusStore();

const loading = shouldShowLoadingScreen(section);
const refreshing = isLoading(section);

const entries = computed(() => {
  const addresses = get(selectedAccounts).map(({ address }) => address);
  const airdrops = get(airdropStore.airdropList(addresses));
  return airdrops
    .filter(airdrop => airdrop.claimed === get(status))
    .map((value, index) => ({
      ...value,
      index
    }));
});

const tableHeaders = computed<DataTableHeader[]>(() => [
  {
    text: t('airdrops.headers.source'),
    value: 'source',
    width: '200px'
  },
  {
    text: t('common.address'),
    value: 'address'
  },
  {
    text: t('common.amount'),
    value: 'amount',
    align: 'end'
  },
  {
    text: t('common.status'),
    value: 'claimed'
  },
  {
    text: '',
    value: 'link',
    align: 'end',
    width: '50px'
  }
]);

const refresh = async () => {
  await airdropStore.fetchAirdrops(true);
};

const getIcon = (source: AirdropType) => sources[source]?.icon ?? '';

const getLabel = (source: AirdropType) => sources[source]?.name ?? '';

const hasDetails = (source: AirdropType): boolean =>
  [AIRDROP_POAP].includes(source);

const expand = (item: Airdrop) => {
  set(expanded, get(expanded).includes(item) ? [] : [item]);
};

onMounted(async () => {
  await airdropStore.fetchAirdrops();
});
</script>

<template>
  <div>
    <VRow class="mt-8">
      <VCol>
        <RefreshHeader
          :loading="refreshing"
          :title="t('airdrops.title')"
          @refresh="refresh()"
        />
      </VCol>
    </VRow>
    <ProgressScreen v-if="loading">
      <template #message>{{ t('airdrops.loading') }}</template>
    </ProgressScreen>
    <div v-else>
      <RuiCard variant="outlined" :class="css.filters">
        <div class="flex space-x-8">
          <BlockchainAccountSelector
            v-model="selectedAccounts"
            multiple
            class="w-full !shadow-none !border-none !p-0"
            no-padding
            hint
            dense
            outlined
            :chains="[ETH]"
            :usable-addresses="airdropAddresses"
          />
          <div class="flex flex-col min-w-[10rem] w-2/5">
            <VSelect
              v-model="status"
              :items="statusFilters"
              item-value="value"
              item-text="text"
              hide-details
              dense
              outlined
            />
            <p class="text-body-1 text-rui-text-secondary mt-0 mb-0">
              {{
                t('airdrops.status_hint', {
                  status: status ? t('common.claimed') : t('common.unclaimed')
                })
              }}
            </p>
          </div>
        </div>
        <div class="text-caption mt-8" v-text="t('airdrops.description')" />
      </RuiCard>
      <VCard class="mt-8">
        <VCardText>
          <DataTable
            :class="css.table"
            :items="entries"
            :headers="tableHeaders"
            single-expand
            :expanded.sync="expanded"
            item-key="index"
          >
            <template #item.address="{ item }">
              <HashLink :text="item.address" />
            </template>
            <template #item.amount="{ item }">
              <AmountDisplay
                v-if="!hasDetails(item.source)"
                :value="item.amount"
                :asset="item.asset"
              />
              <span v-else>{{ item.details.length }}</span>
            </template>
            <template #item.claimed="{ item: { claimed } }">
              <RuiChip
                :color="claimed ? 'success' : 'grey'"
                :label="claimed ? t('common.claimed') : t('common.unclaimed')"
                size="sm"
              />
            </template>
            <template #item.source="{ item }">
              <div class="d-flex flex-row align-center">
                <AdaptiveWrapper>
                  <VImg
                    width="24px"
                    height="24px"
                    contain
                    position="left"
                    max-height="32px"
                    max-width="32px"
                    :src="getIcon(item.source)"
                  />
                </AdaptiveWrapper>
                <span class="ml-4" v-text="getLabel(item.source)" />
              </div>
            </template>
            <template #item.link="{ item }">
              <VBtn
                v-if="!hasDetails(item.source)"
                icon
                color="primary"
                :target="isPackaged ? undefined : '_blank'"
                :href="isPackaged ? undefined : item.link"
                @click="isPackaged ? navigate(item.link) : undefined"
              >
                <VIcon>mdi-link</VIcon>
              </VBtn>
              <RowExpander
                v-else
                :expanded="expanded.includes(item)"
                @click="expand(item)"
              />
            </template>
            <template #expanded-item="{ headers, item }">
              <PoapDeliveryAirdrops
                :items="item.details"
                :colspan="headers.length"
                :visible="hasDetails(item.source)"
              />
            </template>
          </DataTable>
        </VCardText>
      </VCard>
    </div>
  </div>
</template>

<style module lang="scss">
.table {
  tbody {
    tr {
      height: 72px;
    }
  }
}

.filters {
  :global(.v-card__text) {
    @apply px-0 pb-0 #{!important};
  }

  @apply w-full;
}
</style>
