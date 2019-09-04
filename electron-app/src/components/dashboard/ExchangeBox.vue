<template>
  <div class="panel panel-primary">
    <div :id="`${exchange}_box`" class="panel-heading">
      <div class="row">
        <div class="col-xs-3">
          <i
            ><img
              :title="name"
              :class="inverted ? 'exchange-icon-inverted' : 'exchange-icon'"
              :src="require(`../../assets/images/${name}.png`)"
          /></i>
        </div>
        <div class="col-xs-9 text-right">
          <div class="huge">{{ amount }}</div>
          <div id="status_box_text">
            <i id="currencyicon" class="fa" :class="currency.icon"></i>
          </div>
        </div>
      </div>
    </div>
    <a :id="`exchange_${name}_details`">
      <div class="panel-footer">
        <span class="pull-left">View Details</span
        ><span class="pull-right"
          ><i class="fa fa-arrow-circle-right"></i
        ></span>
        <div class="clearfix"></div>
      </div>
    </a></div
></template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { mapState } from 'vuex';
import { Currency } from '@/model/currency';

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
