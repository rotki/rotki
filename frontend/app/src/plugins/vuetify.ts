import 'font-awesome/css/font-awesome.min.css';
import Vue from 'vue';
import Vuetify from 'vuetify/lib';

Vue.use(Vuetify);

export default new Vuetify({
  icons: {
    iconfont: 'fa4'
  },
  theme: {
    themes: {
      light: {
        primary: '#7e4a3b',
        secondary: '#424242',
        accent: '#e45325',
        error: '#FF5252',
        info: '#2196F3',
        success: '#4CAF50',
        warning: '#FFC107',
        rotkigreen: '#06D6A0',
        rotkired: '#F03A47',
        rotkiorange: '#E96930',
        rotkiblack: '#0A0908',
        rotkibeige: '#F2EFEA',
        rotkilightblue: '#96DFD2',
        rotkiblue: '#00CCCC',
        rotkilightbrown: '#664D3E',
        rotkibrown: '#422919',
        rotkiyellow: '#F5CB5C'
      }
    }
  }
});
