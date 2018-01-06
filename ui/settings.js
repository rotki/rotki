function Currency(name, icon, ticker_symbol) {
    this.name = name;
    this.icon = icon;
    this.ticker_symbol = ticker_symbol;
}

function assert_exchange_exists(name) {
    if (EXCHANGES.indexOf(name) < 0) {
        throw "Invalid exchange name: " + name;
    }
}

let exchanges = ['kraken', 'poloniex', 'bittrex'];
let currencies = [
    new Currency("United States Dollar", "fa-usd", "USD"),
    new Currency("Euro", "fa-eur", "EUR"),
    new Currency("British Pound", "fa-gbp", "GBP"),
    new Currency("Japanese Yen", "fa-jpy", "JPY"),
    new Currency("Chinese Yuan", "fa-jpy", "CNY"),
];

module.exports = {
    EXCHANGES: exchanges,
    CURRENCIES: currencies,
    default_currency: currencies[0],
    main_currency: currencies[0],
    current_location: null,
    page_index: null,
    page_external_trades: null,
    page_exchange: {},
    assert_exchange_exists: assert_exchange_exists
};
