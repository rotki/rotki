LINT_PATHS = rotkehlchen/ tools/ setup.py conftest.py package.py
ISORT_PARAMS = --ignore-whitespace --settings-path ./ --skip-glob '*/node_modules/*' $(LINT_PATHS)
ISORT_CHECK_PARAMS = --diff --check-only

lint:
	isort $(ISORT_PARAMS) $(ISORT_CHECK_PARAMS)
	flake8 rotkehlchen/ package.py
	mypy rotkehlchen/ package.py --install-types --non-interactive
	pylint --rcfile .pylint.rc rotkehlchen/ package.py


format:
	isort $(ISORT_PARAMS)


clean:
	rm -rf build/ dist/ rotkehlchen_py_dist/ htmlcov/ rotkehlchen.egg-info/ *.dmg frontend/app/dist/ frontend/app/build/

docker-image:
	packaging/docker-image.sh

test-assets:
	python pytestgeventwrapper.py rotkehlchen/tests/exchanges/test_binance.py::test_binance_assets_are_known
	python pytestgeventwrapper.py rotkehlchen/tests/exchanges/test_bitfinex.py::test_assets_are_known
	python pytestgeventwrapper.py rotkehlchen/tests/exchanges/test_bittrex.py::test_bittrex_assets_are_known
	python pytestgeventwrapper.py rotkehlchen/tests/exchanges/test_bitstamp.py::test_bitstamp_exchange_assets_are_known
	python pytestgeventwrapper.py rotkehlchen/tests/exchanges/test_coinbasepro.py::test_coverage_of_products
	python pytestgeventwrapper.py rotkehlchen/tests/exchanges/test_ftx.py::test_ftx_exchange_assets_are_known
	python pytestgeventwrapper.py rotkehlchen/tests/exchanges/test_kraken.py::test_coverage_of_kraken_balances
	python pytestgeventwrapper.py rotkehlchen/tests/exchanges/test_iconomi.py::test_iconomi_assets_are_known
	python pytestgeventwrapper.py rotkehlchen/tests/exchanges/test_kraken.py::test_kraken_to_world_pair
	python pytestgeventwrapper.py rotkehlchen/tests/exchanges/test_kucoin.py::test_kucoin_exchange_assets_are_known
	python pytestgeventwrapper.py rotkehlchen/tests/exchanges/test_poloniex.py::test_poloniex_assets_are_known
	python pytestgeventwrapper.py rotkehlchen/tests/exchanges/test_gemini.py::test_gemini_all_symbols_are_known
	python pytestgeventwrapper.py rotkehlchen/tests/unit/test_assets.py::test_coingecko_identifiers_are_reachable
	python pytestgeventwrapper.py rotkehlchen/tests/unit/test_assets.py::test_cryptocompare_asset_support
	python pytestgeventwrapper.py rotkehlchen/tests/unit/test_aave.py::test_atoken_to_asset
	python pytestgeventwrapper.py rotkehlchen/tests/exchanges/test_independentreserve.py::test_assets_are_known
	python pytestgeventwrapper.py rotkehlchen/tests/unit/test_zerionsdk.py::test_protocol_names_are_known
	python pytestgeventwrapper.py rotkehlchen/tests/unit/test_zerionsdk.py::test_query_all_protocol_balances_for_account
