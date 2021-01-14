<template>
  <v-form>
    <v-select :label="$t('ledger_actions_form.type.label')" />
    <date-time-picker
      v-model="datetime"
      :label="$t('ledger_actions_form.date.label')"
      persistent-hint
      :hint="$t('ledger_actions_form.date.hint')"
    />
    <asset-select v-model="asset" />
    <v-text-field />
    <v-textarea v-model="link" :label="$t('ledger_actions_form.link.label')" />
    <v-textarea
      v-model="notes"
      outlined
      :label="$t('ledger_actions_form.notes.label')"
    />
  </v-form>
</template>

<script lang="ts">
import { Component, Vue } from 'vue-property-decorator';

@Component({})
export default class LedgerActionForm extends Vue {
  datetime: string = '';
  asset: string = '';
  link: string = '';
  notes: string = '';
}
</script>

<style scoped lang="scss"></style>
