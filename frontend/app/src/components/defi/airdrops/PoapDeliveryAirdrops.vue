<script setup lang="ts">
import { type PropType } from 'vue';
import { type DataTableHeader } from '@/types/vuetify';
import { type PoapDeliveryDetails } from '@/types/airdrops';
import { default as images } from './poap.json';

defineProps({
  visible: { required: true, type: Boolean },
  colspan: { required: true, type: Number },
  items: { required: true, type: Array as PropType<PoapDeliveryDetails[]> }
});

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

const { navigate, isPackaged } = useInterop();
</script>

<template>
  <TableExpandContainer :visible="visible" :colspan="colspan" :padded="false">
    <template #title>
      {{ t('poap_delivery_airdrops.title') }}
    </template>
    <DataTable :items="items" :headers="headers">
      <template #item.name="{ item }">
        <VRow align="center">
          <VCol cols="auto">
            <VImg
              class="poap-delivery-airdrops__image"
              width="36px"
              height="36px"
              contain
              :src="getImage(item.event)"
            />
          </VCol>
          <VCol> {{ item.name }}</VCol>
        </VRow>
      </template>
      <template #item.link="{ item }">
        <VBtn
          icon
          color="primary"
          :target="isPackaged ? undefined : '_blank'"
          :href="isPackaged ? undefined : item.link"
          @click="isPackaged ? navigate(item.link) : undefined"
        >
          <VIcon>mdi-link</VIcon>
        </VBtn>
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
