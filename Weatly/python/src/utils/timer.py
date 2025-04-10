import time
import logging

# Global accumulator could be imported from a central module if needed.
ACCUMULATED_TIMINGS = {}

class Timer:
    def __init__(self, label=""):
        self.label = label
    def __enter__(self):
        self.start = time.perf_counter()
        return self
    def __exit__(self, *args):
        self.end = time.perf_counter()
        self.elapsed = self.end - self.start
        if self.label in ACCUMULATED_TIMINGS:
            total, count = ACCUMULATED_TIMINGS[self.label]
            ACCUMULATED_TIMINGS[self.label] = (total + self.elapsed, count + 1)
        else:
            ACCUMULATED_TIMINGS[self.label] = (self.elapsed, 1)
        logging.info(f"{self.label} took {self.elapsed:.4f} seconds")
