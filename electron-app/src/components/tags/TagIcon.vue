<template>
  <v-chip
    class="tag font-weight-medium"
    label
    :color="`#${tag.background_color}`"
    :text-color="`#${tag.foreground_color}`"
  >
    {{ tag.name }}
  </v-chip>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { Tag } from '@/typing/types';

@Component({})
export default class TagIcon extends Vue {
  @Prop({ required: true })
  tag!: Tag;
}
</script>

<style scoped lang="scss"></style>
