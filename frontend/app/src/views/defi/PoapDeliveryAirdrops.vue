<template>
  <div class="py-4">
    <div class="text-h6 mb-4">{{ $t('poap_delivery_airdrops.title') }}</div>
    <v-sheet outlined rounded>
      <v-data-table
        :items="items"
        :headers="headers"
        must-sort
        :footer-props="footerProps"
      >
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
      </v-data-table>
    </v-sheet>
  </div>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { DataTableHeader } from 'vuetify';
import { footerProps } from '@/config/datatable.common';
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

@Component({})
export default class PoapDeliveryAirdrops extends Vue {
  readonly footerProps = footerProps;
  readonly headers: DataTableHeader[] = [
    {
      text: this.$t('poap_delivery_airdrops.headers.name').toString(),
      value: 'name'
    },
    {
      text: '',
      value: 'link',
      align: 'end',
      width: '50px'
    }
  ];
  @Prop({ required: true, type: Array })
  items!: PoapDeliveryDetails[];

  getImage(event: EventType): string {
    const image = images[event];
    return image ?? '';
  }
}
</script>

<style scoped lang="scss">
.poap-delivery-airdrops {
  &__image {
    border-radius: 50%;
  }
}
</style>
