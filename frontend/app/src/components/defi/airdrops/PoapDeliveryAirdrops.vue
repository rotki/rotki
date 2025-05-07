<script setup lang="ts">
import type { PoapDeliveryDetails } from '@/types/defi/airdrops';
import type { DataTableColumn } from '@rotki/ui-library';
import AppImage from '@/components/common/AppImage.vue';
import images from '@/components/defi/airdrops/poap.json';
import AdaptiveWrapper from '@/components/display/AdaptiveWrapper.vue';
import ExternalLink from '@/components/helper/ExternalLink.vue';

defineProps<{ items: PoapDeliveryDetails[] }>();

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

const { t } = useI18n({ useScope: 'global' });

const headers = computed<DataTableColumn<PoapDeliveryDetails>[]>(() => [
  {
    key: 'name',
    label: t('common.name'),
  },
  {
    align: 'end',
    key: 'link',
    label: '',
    width: '50px',
  },
]);

function isEventType(event: string): event is EventType {
  return Array.prototype.includes.call(events, event);
}

function getImage(event: string): string {
  if (isEventType(event))
    return images[event];

  return '';
}
</script>

<template>
  <RuiCard no-padding>
    <template #header>
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
              name="lu-external-link"
            />
          </RuiButton>
        </ExternalLink>
      </template>
    </RuiDataTable>
  </RuiCard>
</template>
