import time
import unittest

def critical_function():
    # Simulate a critical function
    total = 0
    for i in range(10000):
        total += i
    return total

class TestPerformance(unittest.TestCase):
    def test_performance(self):
        start_time = time.time()
        critical_function()
        end_time = time.time()
        execution_time = end_time - start_time
        self.assertLess(execution_time, 1, "Performance regression detected!")

if __name__ == '__main__':
    unittest.main()