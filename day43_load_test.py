import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

URL = "http://127.0.0.1:8000/api/v1/screener"

def call_api(i):
    start = time.perf_counter()
    response = requests.get(URL, timeout=10)
    elapsed = time.perf_counter() - start

    return i, response.status_code, elapsed


print("=" * 50)
print("DAY 43 - SCREENER LOAD TEST")
print("=" * 50)

start = time.perf_counter()

results = []

with ThreadPoolExecutor(max_workers=10) as executor:
    futures = [
        executor.submit(call_api, i)
        for i in range(10)
    ]

    for future in as_completed(futures):
        results.append(future.result())

total = time.perf_counter() - start

results.sort()

print("\nRESULTS")

for i, status, elapsed in results:
    print(
        f"Request {i + 1:02d}: "
        f"HTTP {status} | "
        f"{elapsed:.3f}s"
    )

print("\n" + "=" * 50)
print(f"Total time: {total:.3f}s")
print(f"Max response: {max(x[2] for x in results):.3f}s")
print("=" * 50)

if all(status == 200 for _, status, _ in results) and total < 10:
    print("PASS - 10 concurrent screener calls completed within 10 seconds")
else:
    print("FAIL - Performance target not met")
