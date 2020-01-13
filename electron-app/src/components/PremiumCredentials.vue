<template>
  <div>
    <v-checkbox
      :value="enabled"
      label="Enable Premium"
      off-icon="fa fa-square-o"
      @change="enabledChanged"
    ></v-checkbox>
    <div v-if="enabled">
      <v-text-field
        :value="apiKey"
        :disabled="loading"
        class="premium-settings__fields__api-key"
        :append-icon="showKey ? 'fa-eye' : 'fa-eye-slash'"
        prepend-icon="fa-key"
        :type="showKey ? 'text' : 'password'"
        :rules="apiKeyRules"
        label="Rotkehlchen API Key"
        @input="apiKeyChanged"
        @click:append="showKey = !showKey"
      ></v-text-field>
      <v-text-field
        :value="apiSecret"
        :disabled="loading"
        class="premium-settings__fields__api-secret"
        :append-icon="showSecret ? 'fa-eye' : 'fa-eye-slash'"
        prepend-icon="fa-user-secret"
        :type="showSecret ? 'text' : 'password'"
        label="Rotkehlchen API Secret"
        :rules="apiSecretRules"
        @input="apiSecretChanged"
        @click:append="showSecret = !showSecret"
      ></v-text-field>
    </div>
  </div>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue, Watch } from 'vue-property-decorator';

@Component({})
export default class PremiumCredentials extends Vue {
  @Prop({ required: true })
  loading!: boolean;
  @Prop({ required: true })
  enabled!: boolean;
  @Prop({ required: true })
  apiSecret!: string;
  @Prop({ required: true })
  apiKey!: string;

  showKey: boolean = false;
  showSecret: boolean = false;

  @Watch('enabled')
  onEnabledChange() {
    if (!this.enabled) {
      this.apiKeyChanged('');
      this.apiSecretChanged('');
    }
  }

  readonly apiKeyRules = [(v: string) => !!v || 'The API key cannot be empty'];
  readonly apiSecretRules = [
    (v: string) => !!v || 'The API secret cannot be empty'
  ];

  @Emit()
  apiKeyChanged(_apiKey: string) {}

  @Emit()
  apiSecretChanged(_apiSecret: string) {}

  @Emit()
  enabledChanged(_enabled: boolean) {}
}
</script>

<style scoped lang="scss"></style>
