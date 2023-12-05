<script setup lang="ts">
import { type DataTableHeader } from '@/types/vuetify';
import { type PoapDeliveryDetails } from '@/types/defi/airdrops';
import { default as images } from './poap.json';

defineProps<{
  visible: boolean;
  colspan: number;
  items: PoapDeliveryDetails[];
}>();

const events = [
  'aave_v2_pioneers',
  'beacon_chain_first_1024',
  'beacon_chain_first_32769',
  'coingecko_yield_farming',
  'eth2_genesis',
  'half_rekt',
  'keep_stakers',
  'lumberjackers',
  'medalla',
  'muir_glacier',
  'proof_of_gucci_design_competition',
  'proof_of_gucci',
  'resuscitators',
  'yam',
  'ycover',
  'yfi_og'
] as const;

type EventType = (typeof events)[number];

const { t } = useI18n();

const headers = computed<DataTableHeader[]>(() => [
  {
    text: t('common.name').toString(),
    value: 'name'
  },
  {
    text: '',
    value: 'link',
    align: 'end',
    width: '50px'
  }
]);

const getImage = (event: EventType): string => {
  const image = images[event];
  return image ?? '';
};
</script>

<template>
  <TableExpandContainer :visible="visible" :colspan="colspan" no-padding>
    <template #title>
      {{ t('poap_delivery_airdrops.title') }}
    </template>
    <DataTable :items="items" :headers="headers">
      <template #item.name="{ item }">
        <div class="flex items-center gap-4">
          <AdaptiveWrapper>
            <VImg
              class="poap-delivery-airdrops__image"
              width="36px"
              height="36px"
              contain
              :src="getImage(item.event)"
            />
          </AdaptiveWrapper>
          <div>{{ item.name }}</div>
        </div>
      </template>
      <template #item.link="{ item }">
        <ExternalLinkButton
          icon
          color="primary"
          :url="item.link"
          variant="text"
        >
          <RuiIcon size="16" name="external-link-line" />
        </ExternalLinkButton>
      </template>
    </DataTable>
  </TableExpandContainer>
</template>

<style scoped lang="scss">
.poap-delivery-airdrops {
  &__image {
    border-radius: 50%;
  }
}
</style>
