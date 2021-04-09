<template>
  <progress-screen v-if="loading">
    <template #message>
      {{ $t('adex_page.loading') }}
    </template>
  </progress-screen>
  <adex-staking
    v-else
    :history-refreshing="secondaryLoading || secondaryRefreshing"
    :refreshing="refreshing"
  />
</template>

<script lang="ts">
import { Component, Mixins } from 'vue-property-decorator';
import { mapActions } from 'vuex';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import StatusMixin from '@/mixins/status-mixin';
import { AdexStaking } from '@/premium/premium';
import { Section } from '@/store/const';

@Component({
  components: { AdexStaking, ProgressScreen },
  methods: {
    ...mapActions('staking', ['fetchAdex'])
  }
})
export default class AdexPage extends Mixins(StatusMixin) {
  section = Section.STAKING_ADEX;
  secondSection = Section.STAKING_ADEX_HISTORY;

  fetchAdex!: (refresh: boolean) => Promise<void>;

  async mounted() {
    await this.fetchAdex(false);
  }
}
</script>

<style scoped lang="scss"></style>
