COMMON_LINT_PATHS = rotkehlchen/ rotkehlchen_mock/ package.py docs/conf.py packaging/docker/entrypoint.py
TOOLS_LINT_PATH = tools/
ALL_LINT_PATHS = $(COMMON_LINT_PATHS) $(TOOLS_LINT_PATH)

lint:
	ruff check $(ALL_LINT_PATHS)
	double-indent --dry-run $(ALL_LINT_PATHS)
	mypy $(COMMON_LINT_PATHS) --install-types --non-interactive
	PYRIGHT_PYTHON_IGNORE_WARNINGS=1 pyright $(COMMON_LINT_PATHS)
	pylint --rcfile .pylint.rc $(ALL_LINT_PATHS)


format:
	ruff check $(ALL_LINT_PATHS) --fix
	double-indent $(ALL_LINT_PATHS)


clean:
	rm -rf build/ dist/ rotkehlchen_py_dist/ htmlcov/ rotkehlchen.egg-info/ *.dmg frontend/app/dist/ frontend/app/build/


docker-image:
	packaging/docker-image.sh


test-assets:
	uv run pytestgeventwrapper.py rotkehlchen/tests/exchanges/test_binance.py::test_binance_assets_are_known
	uv run pytestgeventwrapper.py rotkehlchen/tests/exchanges/test_binance_us.py::test_binance_assets_are_known
	uv run pytestgeventwrapper.py rotkehlchen/tests/exchanges/test_bitfinex.py::test_assets_are_known
	uv run pytestgeventwrapper.py rotkehlchen/tests/exchanges/test_bitstamp.py::test_bitstamp_exchange_assets_are_known
	uv run pytestgeventwrapper.py rotkehlchen/tests/exchanges/test_coinbase.py::test_coverage_of_products
	uv run pytestgeventwrapper.py rotkehlchen/tests/exchanges/test_kraken.py::test_coverage_of_kraken_balances
	uv run pytestgeventwrapper.py rotkehlchen/tests/exchanges/test_iconomi.py::test_iconomi_assets_are_known
	uv run pytestgeventwrapper.py rotkehlchen/tests/exchanges/test_kucoin.py::test_kucoin_exchange_assets_are_known
	uv run pytestgeventwrapper.py rotkehlchen/tests/exchanges/test_poloniex.py::test_poloniex_assets_are_known
	uv run pytestgeventwrapper.py rotkehlchen/tests/exchanges/test_gemini.py::test_gemini_all_symbols_are_known
	uv run pytestgeventwrapper.py rotkehlchen/tests/exchanges/test_okx.py::test_assets_are_known
	uv run pytestgeventwrapper.py rotkehlchen/tests/unit/test_assets.py::test_coingecko_identifiers_are_reachable
	uv run pytestgeventwrapper.py rotkehlchen/tests/unit/test_assets.py::test_cryptocompare_asset_support
	uv run pytestgeventwrapper.py rotkehlchen/tests/exchanges/test_independentreserve.py::test_assets_are_known
	uv run pytestgeventwrapper.py rotkehlchen/tests/unit/test_zerionsdk.py::test_protocol_names_are_known
	uv run pytestgeventwrapper.py rotkehlchen/tests/unit/test_zerionsdk.py::test_query_all_protocol_balances_for_account
	uv run pytestgeventwrapper.py rotkehlchen/tests/exchanges/test_woo.py::test_woo_assets_are_known
	uv run pytestgeventwrapper.py rotkehlchen/tests/exchanges/test_bybit.py::test_assets_are_known

create-cassettes:
	RECORD_CASSETTES=true uv run pytestgeventwrapper.py -m vcr rotkehlchen/tests

create-cassette:
	RECORD_CASSETTES=true uv run pytestgeventwrapper.py -m vcr $(filter-out $@,$(MAKECMDGOALS))



# A macro to catch extra makefile arguments and use them elsewhere
# https://stackoverflow.com/a/6273809/110395
%:
	@:
