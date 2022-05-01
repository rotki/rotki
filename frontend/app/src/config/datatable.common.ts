import i18n from '@/i18n';

export const footerProps = {
  itemsPerPageText: i18n.t('data_table.rows_per_page').toString(),
  showFirstLastPage: true,
  firstIcon: 'mdi-chevron-double-left',
  lastIcon: 'mdi-chevron-double-right',
  prevIcon: 'mdi-chevron-left',
  nextIcon: 'mdi-chevron-right',
  'items-per-page-options': [10, 25, 50, 100]
};
