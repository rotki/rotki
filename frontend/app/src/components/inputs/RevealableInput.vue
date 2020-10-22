<template>
  <v-text-field
    v-bind="$attrs"
    :value="value"
    class="revealable-input"
    :prepend-icon="prependIcon"
    :type="revealed ? 'text' : 'password'"
    :rules="rules"
    :label="label"
    :hint="hint"
    :disabled="disabled"
    :persistent-hint="!!hint"
    :error-messages="errorMessages"
    v-on="$listeners"
    @input="input"
  >
    <template #append>
      <v-btn tabindex="-1" icon @click="revealed = !revealed">
        <v-icon v-text="revealed ? 'mdi-eye' : 'mdi-eye-off'" />
      </v-btn>
    </template>
  </v-text-field>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue } from 'vue-property-decorator';

@Component({})
export default class RevealableInput extends Vue {
  revealed: boolean = false;

  @Prop({ required: true })
  value!: string;

  @Prop({ required: false, default: () => [] })
  rules!: ((v: string) => boolean | string)[];

  @Prop({ required: false, default: '' })
  label!: string;

  @Prop({ required: false, default: 'mdi-key' })
  prependIcon!: string;

  @Prop({ required: false, default: '' })
  hint!: string;

  @Prop({ required: false, default: '' })
  errorMessages!: string | any[];

  @Prop({ required: false, default: false })
  disabled!: boolean;

  @Emit()
  input(_value: string) {}
}
</script>

<style scoped></style>
