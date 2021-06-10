<template>
  <div>
    <v-combobox
      :value="values"
      :disabled="disabled"
      :items="tags"
      class="tag-input"
      small-chips
      :hide-no-data="!search"
      hide-selected
      :label="label"
      :outlined="outlined"
      :search-input.sync="search"
      item-text="name"
      :menu-props="{ closeOnContentClick: true }"
      item-value="name"
      multiple
      @input="input"
    >
      <template #no-data>
        <v-list-item>
          <span class="subheading">{{ $t('tag_input.create_tag') }}</span>
          <v-chip
            class="ml-2"
            :color="newTagBackground"
            :text-color="newTagForeground"
            label
            small
          >
            {{ search }}
          </v-chip>
        </v-list-item>
      </template>
      <template #selection="{ item, selected, select }">
        <v-chip
          label
          class="font-weight-medium"
          :input-value="selected"
          :color="`#${item.background_color}`"
          :text-color="`#${item.foreground_color}`"
          close
          @click:close="remove(item.name)"
          @click="select"
        >
          {{ item.name }}
        </v-chip>
      </template>
      <template #item="{ item }">
        <template v-if="typeof item !== 'object'">
          <v-list-item-content v-text="item" />
        </template>
        <template v-else>
          <div>
            <tag-icon :tag="item" />
            <span class="tag-input__tag__description">
              {{ item.description }}
            </span>
          </div>
        </template>
      </template>
      <template #append-outer>
        <v-btn
          class="tag-input__manage-tags"
          icon
          text
          color="primary"
          :disabled="disabled"
          @click="manageTags = true"
        >
          <v-icon>mdi-pencil</v-icon>
        </v-btn>
      </template>
    </v-combobox>
    <v-dialog
      :value="!!manageTags"
      max-width="800"
      class="tag-input__tag-manager"
      @input="manageTags = false"
    >
      <tag-manager v-if="!!manageTags" dialog @close="manageTags = false" />
    </v-dialog>
  </div>
</template>

<script lang="ts">
import { Component, Emit, Prop, Vue, Watch } from 'vue-property-decorator';
import { mapActions, mapGetters } from 'vuex';
import TagIcon from '@/components/tags/TagIcon.vue';
import TagManager from '@/components/tags/TagManager.vue';
import { ActionStatus } from '@/store/types';
import { Tag } from '@/typing/types';
import { invertColor, randomColor } from '@/utils/Color';

const valueValidator = (value: any) => {
  if (process.env.NODE_ENV === 'production') {
    return true;
  }
  if (!Array.isArray(value)) {
    return false;
  }
  return (value as Array<any>).every(element => typeof element === 'string');
};

@Component({
  components: { TagIcon, TagManager },
  computed: {
    ...mapGetters('session', ['tags'])
  },
  methods: {
    ...mapActions('session', ['addTag'])
  }
})
export default class TagInput extends Vue {
  @Prop({ required: true, type: Array, validator: valueValidator })
  value!: string[];
  @Prop({ required: false, default: false, type: Boolean })
  disabled!: boolean;
  @Prop({ required: false, type: String, default: 'Tags' })
  label!: string;
  @Prop({ required: false, type: Boolean, default: false })
  outlined!: boolean;
  tags!: Tag[];
  addTag!: (tag: Tag) => Promise<ActionStatus>;
  manageTags: boolean = false;

  search: string = '';
  colorScheme = this.randomScheme();

  @Watch('search')
  onSearchUpdate(keyword: string | null, previous: string | null) {
    if (keyword && !previous) {
      this.colorScheme = this.randomScheme();
    }
  }

  get newTagBackground(): string {
    return `#${this.colorScheme.background_color}`;
  }

  get newTagForeground(): string {
    return `#${this.colorScheme.foreground_color}`;
  }

  get values(): Tag[] {
    return this.tags.filter(({ name }) => this.value.includes(name));
  }

  filter(tag: Tag, queryText: string): boolean {
    const { name, description } = tag;
    const query = queryText.toLocaleLowerCase();
    return (
      name.toLocaleLowerCase().indexOf(query) > -1 ||
      description.toLocaleLowerCase().indexOf(query) > -1
    );
  }

  remove(tag: string) {
    const tags = this.value;
    const index = tags.indexOf(tag);
    this.input([...tags.slice(0, index), ...tags.slice(index + 1)]);
  }

  randomScheme() {
    const backgroundColor = randomColor();
    return {
      background_color: backgroundColor,
      foreground_color: invertColor(backgroundColor)
    };
  }

  tagExists(tagName: string): boolean {
    return this.tags.map(({ name }) => name).includes(tagName);
  }

  async createTag(name: string) {
    const { background_color, foreground_color } = this.colorScheme;
    const tag: Tag = {
      name,
      description: '',
      background_color,
      foreground_color
    };
    return await this.addTag(tag);
  }

  @Emit()
  input(_value: (string | Tag)[]): string[] {
    const tags: string[] = [];
    for (let i = 0; i < _value.length; i++) {
      const element = _value[i];
      if (typeof element === 'string') {
        this.attemptTagCreation(element);
        tags.push(element);
      } else {
        tags.push(element.name);
      }
    }
    return tags;
  }

  private attemptTagCreation(element: string) {
    if (this.tagExists(element)) {
      return;
    }
    this.createTag(element).then(({ success }) => {
      if (!success) {
        this.remove(element);
      }
    });
  }
}
</script>

<style scoped lang="scss">
::v-deep {
  .v-dialog {
    &--active {
      height: 100%;
    }
  }

  .v-text-field {
    &--outlined {
      .v-btn {
        &--icon {
          margin-top: -8px;
        }
      }
    }
  }
}

.tag-input {
  &__tag {
    &__description {
      padding-left: 18px;
    }
  }
}
</style>
