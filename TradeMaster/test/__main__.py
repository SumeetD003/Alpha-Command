import sys
import unittest

suite = unittest.defaultTestLoader.discover('Trademaster.backtest.core.test',
                                            pattern='_test*.py', top_level_dir='Trademaster')
if __name__ == '__main__':
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(not result.wasSuccessful())
