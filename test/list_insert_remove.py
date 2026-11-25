"""Energy of a typical list update: append an item, then pop it, for 30 seconds.

    python3 -m quarch_profiler test/list_insert_remove.py -n 5
"""

import time

from quarch_profiler import measure

SECONDS = 30            # how long to keep appending and popping
LIST_SIZE = 1000        # items in the list (append/pop at the end do not depend on it)
BATCH = 1000            # append/pop pairs between clock checks


@measure("list_append_pop")
def append_pop(seconds=SECONDS):
    """Append to the end and pop from the end, keeping the list at LIST_SIZE.
    Returns the number of append/pop pairs done."""
    items = list(range(LIST_SIZE))
    pairs = 0
    end = time.perf_counter() + seconds
    while time.perf_counter() < end:
        for i in range(BATCH):
            items.append(i)
            items.pop()
        pairs += BATCH
    return pairs


pairs = append_pop()
print(f"list_append_pop: {pairs:,} append/pop pairs in {SECONDS} s "
      f"({pairs / SECONDS:,.0f} per second)")
