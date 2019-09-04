<template>
  <div class="panel panel-primary">
    <div :id="id" class="panel-heading">
      <div class="row">
        <div class="col-xs-3">
          <i title="blockchain_box" class="fa fa-5x" :class="icon"></i>
        </div>
        <div class="col-xs-9 text-right">
          <div class="huge">{{ amount | precision(floatingPrecision) }}</div>
          <div id="status_box_text">
            <i id="currencyicon" class="fa" :class="currency.icon"></i>
          </div>
        </div>
      </div>
    </div>
    <div class="panel-footer"><div class="clearfix"></div></div>
  </div>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { mapGetters, mapState } from 'vuex';
import { Currency } from '@/model/currency';

@Component({
  computed: {
    ...mapState(['currency']),
    ...mapGetters(['floatingPrecision'])
  }
})
export default class InformationBox extends Vue {
  currency!: Currency;
  floatingPrecision!: number;

  @Prop({ default: 0 })
  amount!: number;

  @Prop({ required: true })
  id!: string;

  @Prop({ required: true })
  icon!: string;
}
</script>

<style scoped></style>
