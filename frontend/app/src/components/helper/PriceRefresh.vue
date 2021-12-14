<template>
  <v-btn
    outlined
    color="primary"
    :loading="refreshing"
    :disabled="refreshing || loadingData"
    @click="refreshPrices({ ignoreCache: true })"
  >
    <v-icon left>mdi-refresh</v-icon>
    {{ $t('price_refresh.button') }}
  </v-btn>
</template>

<script lang="ts">
import { Ref } from '@vue/composition-api';
import { mapState } from 'pinia';
import { Component, Mixins } from 'vue-property-decorator';
import { mapActions } from 'vuex';
import StatusMixin from '@/mixins/status-mixin';
import { FetchPricePayload } from '@/store/balances/types';
import { Section } from '@/store/const';
import { useTasks } from '@/store/tasks';
import { TaskType } from '@/types/task-type';

@Component({
  computed: {
    ...mapState(useTasks, ['isTaskRunning'])
  },
  methods: {
    ...mapActions('balances', ['refreshPrices'])
  }
})
export default class PriceRefresh extends Mixins(StatusMixin) {
  readonly section = Section.PRICES;
  isTaskRunning!: (type: TaskType) => Ref<boolean>;
  refreshPrices!: (payload: FetchPricePayload) => Promise<void>;

  get loadingData(): boolean {
    return (
      this.isTaskRunning(TaskType.QUERY_BALANCES).value ||
      this.isTaskRunning(TaskType.QUERY_BLOCKCHAIN_BALANCES).value ||
      this.isTaskRunning(TaskType.QUERY_EXCHANGE_BALANCES).value ||
      this.isTaskRunning(TaskType.MANUAL_BALANCES).value
    );
  }
}
</script>
