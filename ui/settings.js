function Currency(name, icon, ticker_symbol) {
    this.name = name;
    this.icon = icon;
    this.ticker_symbol = ticker_symbol;
}

let EXCHANGES = ['kraken', 'poloniex', 'bittrex'];
let CURRENCIES = [
    new Currency("United States Dollar", "fa-usd", "USD"),
    new Currency("Euro", "fa-eur", "EUR"),
    new Currency("British Pound", "fa-gbp", "GBP"),
    new Currency("Japanese Yen", "fa-jpy", "JPY"),
    new Currency("Chinese Yuan", "fa-jpy", "CNY"),
];
let default_currency = CURRENCIES[0];
let main_currency = default_currency;

let page_index = null;
let page_external_trades = null;

module.exports = {
    EXCHANGES: EXCHANGES,
    CURRENCIES: CURRENCIES,
    default_currency: CURRENCIES[0],
    main_currency: CURRENCIES[0],
    page_index: page_index,
    page_external_trades: page_external_trades
};
