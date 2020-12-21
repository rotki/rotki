<template>
  <v-card>
    <v-alert color="error" icon="mdi-alert" outlined prominent>
      <span
        class="font-weight-medium"
        v-text="$t('premium_loading_failed.title')"
      />
      <p class="mt-1" v-text="$t('premium_loading_failed.description')" />
      <p v-text="$t('premium_loading_failed.try_again')" />
      <p v-text="$t('premium_loading_failed.open_issue')" />
    </v-alert>
  </v-card>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';

@Component({})
export default class PremiumLoadingFailed extends Vue {}
</script>
