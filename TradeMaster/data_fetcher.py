from .options.options_datafetcher import OptionsDataFetcher
from questdb_query import pandas_query, Endpoint, numpy_query


host = '62.72.42.9'
endpoint = Endpoint(host=host, port=9000, https=False, username='admin', password='2Cents#101')
Options_Data_Fetcher = OptionsDataFetcher(endpoint=endpoint)