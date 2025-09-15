

import webbrowser
from TradeMaster import quantstats


quantstats.reports.html(equity_series, benchmark=benchmark_series, output=tear_sheet_path)
print(f"Tear sheet generated and saved to {tear_sheet_path}")
webbrowser.open(f'file://{tear_sheet_path}')