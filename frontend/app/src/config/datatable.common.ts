export const useFooterProps = () => {
  const { tc } = useI18n();
  const footerProps = computed(() => ({
    itemsPerPageText: tc('data_table.rows_per_page'),
    showFirstLastPage: true,
    firstIcon: 'mdi-chevron-double-left',
    lastIcon: 'mdi-chevron-double-right',
    prevIcon: 'mdi-chevron-left',
    nextIcon: 'mdi-chevron-right',
    'items-per-page-options': [10, 25, 50, 100]
  }));
  return {
    footerProps
  };
};
