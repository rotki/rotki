import { Component, Vue } from 'vue-property-decorator';

@Component({
  name: 'ThemeMixin'
})
export default class ThemeMixin extends Vue {
  get dark(): boolean {
    return this.$vuetify.theme.dark;
  }

  get appBarColor(): string | null {
    if (!this.dark) {
      return 'white';
    }
    return null;
  }

  get fontStyle() {
    return {
      color: this.dark ? 'rgba(255,255,255,0.87)' : 'rgba(0,0,0,0.87)'
    };
  }

  get backgroundStyle() {
    return {
      'background-color': this.dark ? '#1e1e1e' : 'white'
    };
  }
}
