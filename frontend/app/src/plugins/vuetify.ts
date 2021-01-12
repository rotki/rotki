/* istanbul ignore file */

import '@mdi/font/css/materialdesignicons.css';
import Vue from 'vue';
import Vuetify from 'vuetify/lib';

Vue.use(Vuetify);

export default new Vuetify({
  icons: {
    iconfont: 'mdi'
  },
  theme: {
    options: {
      customProperties: true
    },
    themes: {
      light: {
        primary: '#7e4a3b',
        secondary: '#0a0908',
        accent: '#e45325',
        'rotki-light-grey': '#f9fafb',
        'rotki-grey': '#9fa6b2',
        'rotki-green': '#06D6A0',
        'rotki-red': '#F03A47',
        'rotki-orange': '#E96930',
        'rotki-black': '#0A0908',
        'rotki-light-blue': '#96DFD2',
        'rotki-blue': '#00CCCC',
        'rotki-light-brown': '#664D3E',
        'rotki-brown': '#422919',
        'rotki-yellow': '#F5CB5C',
        'rotki-gain': '#4caf50',
        'rotki-loss': '#d32f2f',
        error: '#f03a47',
        success: '#06D6A0'
      }
    }
  }
});
