<template>
  <progress-screen v-if="loading">
    <template #message>
      {{ $t('adex_page.loading') }}
    </template>
  </progress-screen>
</template>

<script lang="ts">
import { Component, Mixins } from 'vue-property-decorator';
import { mapActions } from 'vuex';
import ProgressScreen from '@/components/helper/ProgressScreen.vue';
import StatusMixin from '@/mixins/status-mixin';
import { Section } from '@/store/const';

@Component({
  components: { ProgressScreen },
  methods: {
    ...mapActions('staking', ['fetchAdex'])
  }
})
export default class AdexPage extends Mixins(StatusMixin) {
  section = Section.STAKING_ADEX;
  fetchAdex!: (refresh: boolean) => Promise<void>;

  async mounted() {
    await this.fetchAdex(false);
  }
}
</script>

<style scoped lang="scss"></style>
