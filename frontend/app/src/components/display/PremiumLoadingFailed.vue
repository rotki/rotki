<template>
  <v-card>
    <v-alert color="error" icon="fa-warning" outlined prominent>
      <span class="font-weight-medium">
        There was an error loading the component.
      </span>
      <p class="mt-1">
        This might indicate a problem with the premium component service.
        <br />
        Please try again later.
      </p>
      <p>If the problem persists open an issue in our issue tracker.</p>
    </v-alert>
  </v-card>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';

@Component({})
export default class PremiumLoadingFailed extends Vue {}
</script>
