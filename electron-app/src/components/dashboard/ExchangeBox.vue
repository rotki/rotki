<template>
  <v-card :id="`${name}_box`">
    <v-row>
      <v-col cols="3" class="col-xs-3">
        <v-icon
          :title="name"
          :class="inverted ? 'exchange-icon-inverted' : 'exchange-icon'"
          :src="require(`../../assets/images/${name}.png`)"
        />
      </v-col>
      <v-col cols="9" class="text-right">
        <div class="huge">{{ amount }}</div>
        <div id="status_box_text">
          <i id="currencyicon" class="fa" :class="currency.icon"></i>
        </div>
      </v-col>
    </v-row>
    <v-row>
      <a :id="`exchange_${name}_details`">
        <div class="panel-footer">
          <span class="pull-left">View Details</span
          ><span class="pull-right"
            ><i class="fa fa-arrow-circle-right"></i
          ></span>
          <div class="clearfix"></div>
        </div>
      </a>
    </v-row>
  </v-card>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { createNamespacedHelpers } from 'vuex';
import { Currency } from '@/model/currency';

const { mapState } = createNamespacedHelpers('session');
@Component({
  computed: mapState(['currency'])
})
export default class ExchangeBox extends Vue {
  @Prop({ required: true })
  name!: string;
  @Prop({ required: true })
  amount!: number;

  currency!: Currency;

  get inverted(): boolean {
    return ['poloniex', 'binance', 'bitmex'].indexOf(name) > -1;
  }
}
</script>
<style scoped></style>
