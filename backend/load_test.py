"""
Load Testing Script for MyTutorBot
Tests concurrent user capacity and identifies bottlenecks

Usage:
    pip install locust
    locust -f load_test.py --host http://localhost:8000

Then open http://localhost:8089 and simulate users
"""

import json
import random

from locust import HttpUser, between, task


class TutorBotUser(HttpUser):
    """Simulates a student using the tutoring app"""

    # Wait 1-3 seconds between tasks (realistic student behavior)
    wait_time = between(1, 3)

    def on_start(self):
        """Called when a simulated user starts"""
        # Generate a unique user ID
        self.user_id = f"student_{random.randint(1000, 9999)}"
        print(f"[START] User {self.user_id} started session")

    @task(5)  # Higher weight = more frequent
    def ask_question(self):
        """Simulate asking a question (most common action)"""
        questions = [
            "What is the main topic of the lecture?",
            "Can you explain the key concepts?",
            "What are the important points to remember?",
            "How does this relate to previous topics?",
            "Can you summarize the material?",
        ]

        payload = {
            "question": random.choice(questions),
            "mode": random.choice(["direct", "guided", "socratic"]),
            "anon_user_id": self.user_id,
        }

        with self.client.post(
            "/api/query", json=payload, catch_response=True, name="Ask Question"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if "content" in data:
                    response.success()
                else:
                    response.failure("Missing content in response")
            else:
                response.failure(f"Got status {response.status_code}")

    @task(2)
    def get_chat_history(self):
        """Simulate fetching conversation history"""
        payload = {"anon_user_id": self.user_id}

        with self.client.post(
            "/api/history", json=payload, catch_response=True, name="Get History"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status {response.status_code}")

    @task(1)
    def list_pdfs(self):
        """Simulate checking available PDFs"""
        with self.client.get(
            "/api/files", catch_response=True, name="List PDFs"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if "files" in data:
                    response.success()
                else:
                    response.failure("Missing files in response")
            else:
                response.failure(f"Got status {response.status_code}")

    @task(1)
    def health_check(self):
        """Check system health"""
        with self.client.get(
            "/health", catch_response=True, name="Health Check"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Got status {response.status_code}")


class AdminUser(HttpUser):
    """Simulates an admin user (less frequent, different actions)"""

    wait_time = between(5, 15)

    @task(1)
    def check_index_stats(self):
        """Check RAG index statistics"""
        with self.client.post("/api/ingest", catch_response=True) as response:
            # This endpoint can return success or error depending on content
            if response.status_code in [200, 400]:
                response.success()
            else:
                response.failure(f"Got status {response.status_code}")


# Performance Test Scenarios


class QuickTest(HttpUser):
    """Quick test: 10 users for 1 minute"""

    # Run with: locust -f load_test.py --users 10 --spawn-rate 2 --run-time 1m QuickTest
    tasks = [TutorBotUser]
    wait_time = between(1, 2)


class NormalLoad(HttpUser):
    """Normal load: 50 users for 5 minutes"""

    # Run with: locust -f load_test.py --users 50 --spawn-rate 5 --run-time 5m NormalLoad
    tasks = [TutorBotUser]
    wait_time = between(1, 3)


class StressTest(HttpUser):
    """Stress test: 100 users for 10 minutes"""

    # Run with: locust -f load_test.py --users 100 --spawn-rate 10 --run-time 10m StressTest
    tasks = [TutorBotUser]
    wait_time = between(1, 3)


"""
Expected Results (100 concurrent users):

FAST (< 100ms):
- GET /health
- POST /api/history
- GET /api/files

MEDIUM (100-500ms):
- ChromaDB vector search (internal)

SLOW (1-3 seconds):
- POST /api/query (due to Groq LLM API call)

Bottleneck Analysis:
- If /api/query is slow: Groq API limit (expected)
- If /api/history is slow: SQLite write contention → upgrade to PostgreSQL
- If /api/files is slow: S3 API issue or not using S3
- If /health is slow: System resource issue

Success Criteria for 100 Users:
✅ Response time P50 < 3 seconds (LLM limited)
✅ Response time P95 < 5 seconds
✅ Error rate < 1%
✅ No "database is locked" errors
✅ Memory usage < 1GB
"""


import time

# Custom metrics tracking
from locust import events

response_times = []


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Track response times for analysis"""
    if exception is None:
        response_times.append(
            {"endpoint": name, "time_ms": response_time, "timestamp": time.time()}
        )


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Print performance summary after test"""
    if not response_times:
        return

    print("\n" + "=" * 60)
    print("PERFORMANCE SUMMARY")
    print("=" * 60)

    # Group by endpoint
    endpoints = {}
    for rt in response_times:
        ep = rt["endpoint"]
        if ep not in endpoints:
            endpoints[ep] = []
        endpoints[ep].append(rt["time_ms"])

    # Print stats for each endpoint
    for endpoint, times in endpoints.items():
        times.sort()
        count = len(times)
        avg = sum(times) / count
        p50 = times[count // 2]
        p95 = times[int(count * 0.95)] if count > 20 else times[-1]

        print(f"\n{endpoint}:")
        print(f"  Requests: {count}")
        print(f"  Average: {avg:.0f}ms")
        print(f"  P50: {p50:.0f}ms")
        print(f"  P95: {p95:.0f}ms")
        print(f"  Min: {min(times):.0f}ms")
        print(f"  Max: {max(times):.0f}ms")

    print("\n" + "=" * 60)
    print("Bottleneck Analysis:")

    query_times = endpoints.get("Ask Question", [])
    if query_times and sum(query_times) / len(query_times) > 3000:
        print("⚠️  Query times > 3s: Groq API bottleneck (expected)")

    history_times = endpoints.get("Get History", [])
    if history_times and sum(history_times) / len(history_times) > 100:
        print("⚠️  History times > 100ms: Consider PostgreSQL")

    files_times = endpoints.get("List PDFs", [])
    if files_times and sum(files_times) / len(files_times) > 200:
        print("⚠️  PDF listing slow: Check S3 configuration")

    print("=" * 60)
