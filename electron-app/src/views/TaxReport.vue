<template>
  <v-container>
    <v-layout column class="tax-report">
      <v-layout>
        <v-flex xs12>
          <h1>Tax Report</h1>
        </v-flex>
      </v-layout>
      <v-layout>
        <v-flex xs12>
          <v-form>
            <v-text-field></v-text-field>
            <v-text-field></v-text-field>
          </v-form>
        </v-flex>
      </v-layout>
    </v-layout>
    <div id="tax-report"></div>
  </v-container>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';

@Component({})
export default class TaxReport extends Vue {
  mounted() {}
}
</script>

<style scoped></style>
