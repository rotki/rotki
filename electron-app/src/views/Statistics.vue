<template>
  <v-container>
    <div id="statistics">
      <div class="row">
        <div class="col-lg-12">
          <h1 class="page-header">Statistics</h1>
        </div>
      </div>
      <div v-if="!premium">
        No premium subscription detected. Statistics are only available to
        premium users. <br />
        To get a premium subscription please visit our
        <a href="https://rotkehlchen.io/products" target="_blank">website</a>.
      </div>
    </div>
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';
import { mapState } from 'vuex';
import MessageDialog from '@/components/dialogs/MessageDialog.vue';
import { Message } from '@/store/store';

@Component({
  components: { MessageDialog },
  computed: mapState(['premium'])
})
export default class Statistics extends Vue {
  premium!: boolean;

  mounted() {
    if (!this.premium) {
      return;
    }

    this.$rpc
      .query_statistics_renderer()
      .then(result => {
        eval(result);
      })
      .catch(reason => {
        const { commit } = this.$store;
        commit('setMessage', {
          title: 'Error at querying statistics renderer',
          description: reason.message
        } as Message);
      });
  }
}
</script>

<style scoped></style>
