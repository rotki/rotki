<template>
  <v-layout>
    <v-flex>
      <v-card>
        <v-toolbar card>Premium Settings</v-toolbar>
        <v-card-text>
          <v-text-field
            id="premium_api_key_entry"
            v-model="apiKey"
            label="Rotkehlchen API Key"
            type="text"
          ></v-text-field>

          <v-text-field
            id="premium_api_secret_entry"
            v-model="apiSecret"
            label="Rotkehlchen API Key"
            type="text"
          ></v-text-field>
        </v-card-text>
        <v-card-actions>
          <v-btn
            id="setup_premium_button"
            depressed
            color="primary"
            type="submit"
            @click="setupPremium()"
          >
            Setup
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-flex>
  </v-layout>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';

@Component({})
export default class PremiumSettings extends Vue {
  apiKey: string = '';
  apiSecret: string = '';

  setupPremium() {}
}
</script>

<style scoped></style>
