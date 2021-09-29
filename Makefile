lint:
	flake8 rotkehlchen/ tools/data_faker
	mypy rotkehlchen/ tools/data_faker --install-types --non-interactive
	pylint --rcfile .pylint.rc rotkehlchen/ tools/data_faker

clean:
	rm -rf build/ rotkehlchen_py_dist/ htmlcov/ rotkehlchen.egg-info/ *.dmg frontend/app/dist/

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
	python pytestgeventwrapper.py rotkehlchen/tests/exchanges/test_kraken.py::test_kraken_to_world_pair
	python pytestgeventwrapper.py rotkehlchen/tests/exchanges/test_kucoin.py::test_kucoin_exchange_assets_are_known
	python pytestgeventwrapper.py rotkehlchen/tests/exchanges/test_poloniex.py::test_poloniex_assets_are_known
	python pytestgeventwrapper.py rotkehlchen/tests/exchanges/test_gemini.py::test_gemini_all_symbols_are_known
	python pytestgeventwrapper.py rotkehlchen/tests/unit/test_assets.py::test_coingecko_identifiers_are_reachable
	python pytestgeventwrapper.py rotkehlchen/tests/unit/test_assets.py::test_cryptocompare_asset_support