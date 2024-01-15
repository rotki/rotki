<script setup lang="ts">
import images from './poap.json';
import type { DataTableColumn } from '@rotki/ui-library-compat';
import type { PoapDeliveryDetails } from '@/types/defi/airdrops';

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
  'yfi_og',
] as const;

type EventType = (typeof events)[number];

const { t } = useI18n();

const headers = computed<DataTableColumn[]>(() => [
  {
    label: t('common.name'),
    key: 'name',
  },
  {
    label: '',
    key: 'link',
    align: 'end',
    width: '50px',
  },
]);

function getImage(event: EventType): string {
  const image = images[event];
  return image ?? '';
}
</script>

<template>
  <TableExpandContainer
    :visible="visible"
    :colspan="colspan"
    no-padding
  >
    <template #title>
      {{ t('poap_delivery_airdrops.title') }}
    </template>

    <RuiDataTable
      :rows="items"
      :cols="headers"
      row-attr="name"
    >
      <template #item.name="{ row }">
        <div class="flex items-center gap-4">
          <AdaptiveWrapper>
            <AppImage
              class="rounded-full"
              width="36px"
              height="36px"
              contain
              :src="getImage(row.event)"
            />
          </AdaptiveWrapper>

          <div>{{ row.name }}</div>
        </div>
      </template>

      <template #item.link="{ row }">
        <ExternalLink
          :url="row.link"
          custom
        >
          <RuiButton
            variant="text"
            color="primary"
            icon
          >
            <RuiIcon
              size="16"
              name="external-link-line"
            />
          </RuiButton>
        </ExternalLink>
      </template>
    </RuiDataTable>
  </TableExpandContainer>
</template>
