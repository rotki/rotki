<template>
  <v-btn
    outlined
    color="primary"
    :loading="refreshing"
    :disabled="refreshing || loadingData"
    @click="refreshPrices"
  >
    <v-icon left>mdi-refresh</v-icon>
    {{ $t('price_refresh.button') }}
  </v-btn>
</template>

<script lang="ts">
import { Component, Mixins } from 'vue-property-decorator';
import { mapActions, mapGetters } from 'vuex';
import StatusMixin from '@/mixins/status-mixin';
import { TaskType } from '@/model/task-type';
import { Section } from '@/store/const';

@Component({
  computed: {
    ...mapGetters('tasks', ['isTaskRunning'])
  },
  methods: {
    ...mapActions('balances', ['refreshPrices'])
  }
})
export default class PriceRefresh extends Mixins(StatusMixin) {
  readonly section = Section.PRICES;
  isTaskRunning!: (type: TaskType) => boolean;
  refreshPrices!: () => Promise<void>;

  get loadingData(): boolean {
    return (
      this.isTaskRunning(TaskType.QUERY_BALANCES) ||
      this.isTaskRunning(TaskType.QUERY_BLOCKCHAIN_BALANCES) ||
      this.isTaskRunning(TaskType.QUERY_EXCHANGE_BALANCES) ||
      this.isTaskRunning(TaskType.MANUAL_BALANCES)
    );
  }
}
</script>

<style scoped lang="scss"></style>
