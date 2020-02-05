<template>
  <v-text-field
    :value="value"
    class="revealable-input"
    :append-icon="revealed ? 'fa-eye' : 'fa-eye-slash'"
    :prepend-icon="icon"
    :type="revealed ? 'text' : 'password'"
    :rules="rules"
    :label="label"
    :hint="hint"
    :disabled="disabled"
    :persistent-hint="!!hint"
    @input="input"
    @click:append="revealed = !revealed"
  ></v-text-field>
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

  @Prop({ required: false, default: 'fa-key' })
  icon!: string;

  @Prop({ required: false, default: '' })
  hint!: string;

  @Prop({ required: false, default: false })
  disabled!: boolean;

  @Emit()
  input(_value: string) {}
}
</script>

<style scoped></style>
