<template>
  <v-layout>
    <v-flex>
      <v-card>
        <v-toolbar card>Premium Settings</v-toolbar>
        <v-card-text>
          <v-text-field
            id="premium_api_key_entry"
            v-model="apiKey"
            prepend-icon="fa-key"
            label="Rotkehlchen API Key"
            type="text"
          ></v-text-field>

          <v-text-field
            id="premium_api_secret_entry"
            v-model="apiSecret"
            prepend-icon="fa-user-secret"
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
            :disable="premium"
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
import { mapState } from 'vuex';

@Component({
  computed: mapState(['premium'])
})
export default class PremiumSettings extends Vue {
  apiKey: string = '';
  apiSecret: string = '';

  premium!: boolean;

  setupPremium() {}
}
</script>

<style scoped></style>
