export const TableSymbol = Symbol.for('rui:table');

export const libraryDefaults = {
  [TableSymbol.valueOf()]: {
    itemsPerPage: ref(10),
    globalItemsPerPage: false,
    limits: [10, 25, 50, 100],
  },
};
