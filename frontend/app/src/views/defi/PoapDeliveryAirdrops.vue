<template>
  <table-expand-container :visible="visible" :colspan="colspan" :padded="false">
    <template #title>
      {{ $t('poap_delivery_airdrops.title') }}
    </template>
    <data-table :items="items" :headers="headers">
      <template #item.name="{ item }">
        <v-row align="center">
          <v-col cols="auto">
            <v-img
              class="poap-delivery-airdrops__image"
              width="36px"
              height="36px"
              contain
              :src="getImage(item.event)"
            />
          </v-col>
          <v-col> {{ item.name }}</v-col>
        </v-row>
      </template>
      <template #item.link="{ item }">
        <v-btn
          icon
          color="primary"
          :target="$interop.isPackaged ? undefined : '_blank'"
          :href="$interop.isPackaged ? undefined : item.link"
          @click="
            $interop.isPackaged ? $interop.navigate(item.link) : undefined
          "
        >
          <v-icon>mdi-link</v-icon>
        </v-btn>
      </template>
    </data-table>
  </table-expand-container>
</template>

<script lang="ts">
import { defineComponent, PropType } from '@vue/composition-api';
import { DataTableHeader } from 'vuetify';
import DataTable from '@/components/helper/DataTable.vue';
import TableExpandContainer from '@/components/helper/table/TableExpandContainer.vue';
import i18n from '@/i18n';
import { PoapDeliveryDetails } from '@/store/defi/types';
import { default as images } from './poap.json';

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

export type EventType = typeof events[number];

const headers: DataTableHeader[] = [
  {
    text: i18n.t('poap_delivery_airdrops.headers.name').toString(),
    value: 'name'
  },
  {
    text: '',
    value: 'link',
    align: 'end',
    width: '50px'
  }
];

export default defineComponent({
  name: 'PoapDeliveryAirdrops',
  components: { DataTable, TableExpandContainer },
  props: {
    visible: { required: true, type: Boolean },
    colspan: { required: true, type: Number },
    items: { required: true, type: Array as PropType<PoapDeliveryDetails[]> }
  },
  setup() {
    const getImage = (event: EventType): string => {
      const image = images[event];
      return image ?? '';
    };

    return {
      headers,
      getImage
    };
  }
});
</script>

<style scoped lang="scss">
.poap-delivery-airdrops {
  &__image {
    border-radius: 50%;
  }
}
</style>
