#!/usr/bin/env python3
"""
Hybrid Search Performance Benchmarks

This script runs comprehensive performance benchmarks for the hybrid search system,
including latency, throughput, and resource utilization measurements.
"""

import asyncio
import time
import json
import statistics
import sys
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
import psutil
import tracemalloc

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from onyx_core.services.hybrid_search_service import HybridSearchService
from onyx_core.services.keyword_search_service import KeywordSearchService
from onyx_core.rag_service import get_rag_service


class HybridSearchBenchmark:
    """Benchmark suite for hybrid search performance"""

    def __init__(self):
        self.results = {
            "benchmark_info": {
                "timestamp": datetime.now().isoformat(),
                "python_version": sys.version,
                "platform": os.name,
                "cpu_count": psutil.cpu_count(),
                "memory_total_gb": psutil.virtual_memory().total / (1024**3),
            },
            "performance_metrics": {},
            "latency_analysis": {},
            "throughput_tests": {},
            "resource_utilization": {},
            "query_patterns": {}
        }

        self.queries = self._generate_test_queries()
        self.service = None

    def _generate_test_queries(self) -> List[Dict[str, str]]:
        """Generate diverse test queries for comprehensive benchmarking"""
        return [
            # Semantic-dominant queries
            {"query": "what is artificial intelligence", "type": "semantic", "category": "concept"},
            {"query": "how to improve team productivity", "type": "semantic", "category": "process"},
            {"query": "explain machine learning algorithms", "type": "semantic", "category": "technical"},
            {"query": "describe cloud computing benefits", "type": "semantic", "category": "technology"},
            {"query": "summarize quarterly financial results", "type": "semantic", "category": "business"},

            # Keyword-dominant queries
            {"query": "project-unicorn launch date", "type": "keyword", "category": "project"},
            {"query": "ticket-1234 status update", "type": "keyword", "category": "support"},
            {"query": "user@example.com contact information", "type": "keyword", "category": "contact"},
            {"query": "file:/path/to/document.pdf", "type": "keyword", "category": "document"},
            {"query": "https://example.com/api/v1", "type": "keyword", "category": "url"},

            # Mixed queries
            {"query": "customer feedback on AI features", "type": "mixed", "category": "feedback"},
            {"query": "budget allocation for Q4 2025", "type": "mixed", "category": "finance"},
            {"query": "technical specifications and requirements", "type": "mixed", "category": "requirements"},
            {"query": "implementation strategy and timeline", "type": "mixed", "category": "planning"},
            {"query": "performance metrics and monitoring", "type": "mixed", "category": "operations"},

            # Short queries (performance test)
            {"query": "AI", "type": "short", "category": "quick"},
            {"query": "budget", "type": "short", "category": "quick"},
            {"query": "project", "type": "short", "category": "quick"},
            {"query": "data", "type": "short", "category": "quick"},

            # Long queries (complexity test)
            {"query": "comprehensive analysis of machine learning implementation strategies including technical requirements, budget constraints, and timeline considerations for enterprise adoption", "type": "long", "category": "complex"},

            # Fuzzy/partial queries
            {"query": "artifical intel", "type": "fuzzy", "category": "spelling"},
            {"query": "projct unicron", "type": "fuzzy", "category": "spelling"},
        ]

    async def setup(self):
        """Initialize benchmark environment"""
        print("Setting up benchmark environment...")

        # Initialize search service
        self.service = HybridSearchService()
        await self.service._ensure_services_initialized()

        # Enable memory tracking
        tracemalloc.start()

        print(f"Initialized hybrid search service")
        print(f"Generated {len(self.queries)} test queries")

    async def cleanup(self):
        """Clean up benchmark environment"""
        print("Cleaning up benchmark environment...")

        if self.service:
            await self.service.close()

        # Get final memory usage
        current, peak = tracemalloc.get_traced_memory()
        print(f"Memory usage: Current={current/(1024**2):.1f}MB, Peak={peak/(1024**2):.1f}MB")

        tracemalloc.stop()

    async def benchmark_latency(self) -> Dict[str, Any]:
        """Benchmark search latency across different query types"""
        print("\n" + "="*60)
        print("LATENCY BENCHMARK")
        print("="*60)

        latency_results = []

        for i, query_info in enumerate(self.queries):
            print(f"Testing query {i+1}/{len(self.queries)}: {query_info['query'][:50]}...")

            # Warm-up
            await self.service.search(query_info["query"], ["*"], limit=5)

            # Measure latency (multiple runs for accuracy)
            latencies = []
            for _ in range(3):
                start_time = time.time()
                results = await self.service.search(
                    query=query_info["query"],
                    user_permissions=["*"],
                    limit=5
                )
                end_time = time.time()
                latencies.append((end_time - start_time) * 1000)  # Convert to ms

            avg_latency = statistics.mean(latencies)
            min_latency = min(latencies)
            max_latency = max(latencies)
            result_count = len(results)

            latency_result = {
                "query": query_info["query"],
                "query_type": query_info["type"],
                "category": query_info["category"],
                "result_count": result_count,
                "latency_avg_ms": round(avg_latency, 2),
                "latency_min_ms": round(min_latency, 2),
                "latency_max_ms": round(max_latency, 2),
                "latencies": [round(l, 2) for l in latencies]
            }

            latency_results.append(latency_result)
            print(f"  Results: {result_count}, Latency: {avg_latency:.2f}ms avg")

        # Calculate statistics by query type
        stats_by_type = {}
        for result in latency_results:
            query_type = result["query_type"]
            if query_type not in stats_by_type:
                stats_by_type[query_type] = {
                    "latencies": [],
                    "result_counts": [],
                    "categories": set()
                }

            stats_by_type[query_type]["latencies"].append(result["latency_avg_ms"])
            stats_by_type[query_type]["result_counts"].append(result["result_count"])
            stats_by_type[query_type]["categories"].add(result["category"])

        # Calculate final statistics
        all_latencies = [r["latency_avg_ms"] for r in latency_results]

        self.results["latency_analysis"] = {
            "overall": {
                "total_queries": len(latency_results),
                "latency_avg_ms": round(statistics.mean(all_latencies), 2),
                "latency_median_ms": round(statistics.median(all_latencies), 2),
                "latency_p90_ms": round(statistics.quantiles(all_latencies, n=10)[8], 2),
                "latency_p95_ms": round(statistics.quantiles(all_latencies, n=20)[18], 2),
                "latency_p99_ms": round(statistics.quantiles(all_latencies, n=100)[98], 2),
                "latency_min_ms": round(min(all_latencies), 2),
                "latency_max_ms": round(max(all_latencies), 2)
            },
            "by_query_type": {},
            "target_compliance": {
                "p95_under_200ms": statistics.quantiles(all_latencies, n=20)[18] <= 200,
                "average_under_150ms": statistics.mean(all_latencies) <= 150,
                "max_under_400ms": max(all_latencies) <= 400
            }
        }

        for query_type, stats in stats_by_type.items():
            latencies = stats["latencies"]
            self.results["latency_analysis"]["by_query_type"][query_type] = {
                "query_count": len(latencies),
                "latency_avg_ms": round(statistics.mean(latencies), 2),
                "latency_median_ms": round(statistics.median(latencies), 2),
                "latency_p95_ms": round(statistics.quantiles(latencies, n=20)[18], 2),
                "categories": list(stats["categories"]),
                "avg_results": round(statistics.mean(stats["result_counts"]), 1)
            }

        print(f"\nLatency Benchmark Summary:")
        overall = self.results["latency_analysis"]["overall"]
        print(f"  Total queries: {overall['total_queries']}")
        print(f"  Average latency: {overall['latency_avg_ms']}ms")
        print(f"  P95 latency: {overall['latency_p95_ms']}ms")
        print(f"  Target compliance: {overall['target_compliance']['p95_under_200ms']}")

        return latency_results

    async def benchmark_throughput(self) -> Dict[str, Any]:
        """Benchmark search throughput under concurrent load"""
        print("\n" + "="*60)
        print("THROUGHPUT BENCHMARK")
        print("="*60)

        throughput_tests = [
            {"concurrent_users": 1, "duration_seconds": 10},
            {"concurrent_users": 5, "duration_seconds": 10},
            {"concurrent_users": 10, "duration_seconds": 10},
            {"concurrent_users": 20, "duration_seconds": 10},
        ]

        throughput_results = []

        for test_config in throughput_tests:
            concurrent_users = test_config["concurrent_users"]
            duration = test_config["duration_seconds"]

            print(f"Testing {concurrent_users} concurrent users for {duration} seconds...")

            # Create search tasks
            async def perform_search(user_id):
                queries_completed = 0
                start_time = time.time()

                while time.time() - start_time < duration:
                    query = self.queries[user_id % len(self.queries)]
                    await self.service.search(
                        query=query["query"],
                        user_permissions=["*"],
                        limit=5
                    )
                    queries_completed += 1
                    # Small delay to prevent overwhelming the system
                    await asyncio.sleep(0.01)

                return queries_completed

            # Execute concurrent searches
            start_time = time.time()
            tasks = [perform_search(i) for i in range(concurrent_users)]
            results_per_user = await asyncio.gather(*tasks, return_exceptions=True)

            end_time = time.time()
            actual_duration = end_time - start_time

            # Calculate metrics
            successful_users = [r for r in results_per_user if not isinstance(r, Exception)]
            total_queries = sum(successful_users)
            queries_per_second = total_queries / actual_duration
            avg_queries_per_user = total_queries / len(successful_users) if successful_users else 0

            throughput_result = {
                "concurrent_users": concurrent_users,
                "duration_seconds": round(actual_duration, 2),
                "successful_users": len(successful_users),
                "total_queries": total_queries,
                "queries_per_second": round(queries_per_second, 2),
                "avg_queries_per_user": round(avg_queries_per_user, 1),
                "target_compliance": {
                    "min_10_qps": queries_per_second >= 10,
                    "min_50_qps_for_single_user": queries_per_second >= 50 if concurrent_users == 1 else False
                }
            }

            throughput_results.append(throughput_result)
            print(f"  QPS: {queries_per_second:.2f}, Avg per user: {avg_queries_per_user:.1f}")

        self.results["throughput_tests"] = {
            "test_results": throughput_results,
            "max_qps": max(r["queries_per_second"] for r in throughput_results),
            "max_concurrent_users": max(r["concurrent_users"] for r in throughput_results),
            "target_compliance": {
                "achieved_10_qps": any(r["target_compliance"]["min_10_qps"] for r in throughput_results),
                "achieved_50_qps_single": any(r["target_compliance"]["min_50_qps_for_single_user"] for r in throughput_results if r["concurrent_users"] == 1)
            }
        }

        print(f"\nThroughput Benchmark Summary:")
        max_qps = self.results["throughput_tests"]["max_qps"]
        max_users = self.results["throughput_tests"]["max_concurrent_users"]
        print(f"  Maximum QPS: {max_qps}")
        print(f"  Maximum concurrent users tested: {max_users}")

        return throughput_results

    async def benchmark_resource_utilization(self) -> Dict[str, Any]:
        """Benchmark resource utilization during search operations"""
        print("\n" + "="*60)
        print("RESOURCE UTILIZATION BENCHMARK")
        print("="*60)

        # Get baseline resource usage
        baseline_cpu = psutil.cpu_percent(interval=1)
        baseline_memory = psutil.virtual_memory()

        print(f"Baseline CPU: {baseline_cpu:.1f}%")
        print(f"Baseline Memory: {baseline_memory.percent:.1f}%")

        # Monitor resources during search operations
        cpu_samples = []
        memory_samples = []

        monitoring_duration = 30  # seconds
        print(f"Monitoring resource usage for {monitoring_duration} seconds...")

        async def monitor_resources():
            while True:
                cpu_samples.append(psutil.cpu_percent())
                memory_samples.append(psutil.virtual_memory().percent)
                await asyncio.sleep(0.5)

        # Start monitoring
        monitor_task = asyncio.create_task(monitor_resources())

        try:
            # Perform searches during monitoring
            search_start = time.time()
            queries_completed = 0

            while time.time() - search_start < monitoring_duration:
                query = self.queries[queries_completed % len(self.queries)]
                await self.service.search(
                    query=query["query"],
                    user_permissions=["*"],
                    limit=5
                )
                queries_completed += 1
                await asyncio.sleep(0.2)  # Small delay between queries

        finally:
            # Stop monitoring
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass

        # Calculate resource statistics
        self.results["resource_utilization"] = {
            "monitoring_duration_seconds": monitoring_duration,
            "queries_completed": queries_completed,
            "cpu_usage": {
                "avg_percent": round(statistics.mean(cpu_samples), 1),
                "max_percent": round(max(cpu_samples), 1),
                "min_percent": round(min(cpu_samples), 1),
                "baseline_percent": baseline_cpu
            },
            "memory_usage": {
                "avg_percent": round(statistics.mean(memory_samples), 1),
                "max_percent": round(max(memory_samples), 1),
                "min_percent": round(min(memory_samples), 1),
                "baseline_percent": baseline_memory.percent
            },
            "queries_per_second": round(queries_completed / monitoring_duration, 2)
        }

        cpu_stats = self.results["resource_utilization"]["cpu_usage"]
        memory_stats = self.results["resource_utilization"]["memory_usage"]

        print(f"\nResource Utilization Summary:")
        print(f"  CPU: Avg {cpu_stats['avg_percent']}%, Max {cpu_stats['max_percent']}%")
        print(f"  Memory: Avg {memory_stats['avg_percent']}%, Max {memory_stats['max_percent']}%")
        print(f"  Queries per second: {self.results['resource_utilization']['queries_per_second']}")

        return self.results["resource_utilization"]

    async def benchmark_query_patterns(self) -> Dict[str, Any]:
        """Benchmark performance by query type and complexity"""
        print("\n" + "="*60)
        print("QUERY PATTERN BENCHMARK")
        print("="*60)

        pattern_results = {}

        # Group queries by type and category
        query_groups = {}
        for query in self.queries:
            query_type = query["type"]
            category = query["category"]

            if query_type not in query_groups:
                query_groups[query_type] = {}
            if category not in query_groups[query_type]:
                query_groups[query_type][category] = []

            query_groups[query_type][category].append(query)

        for query_type, categories in query_groups.items():
            pattern_results[query_type] = {}

            for category, queries in categories.items():
                print(f"Testing {query_type} - {category}...")

                latencies = []
                result_counts = []

                for query in queries:
                    # Measure performance
                    start_time = time.time()
                    results = await self.service.search(
                        query=query["query"],
                        user_permissions=["*"],
                        limit=5
                    )
                    end_time = time.time()

                    latencies.append((end_time - start_time) * 1000)
                    result_counts.append(len(results))

                pattern_results[query_type][category] = {
                    "query_count": len(queries),
                    "latency_avg_ms": round(statistics.mean(latencies), 2),
                    "latency_p95_ms": round(statistics.quantiles(latencies, n=20)[18], 2),
                    "avg_results": round(statistics.mean(result_counts), 1),
                    "min_results": min(result_counts),
                    "max_results": max(result_counts)
                }

                print(f"  {len(queries)} queries, Avg latency: {pattern_results[query_type][category]['latency_avg_ms']}ms")

        self.results["query_patterns"] = pattern_results

        print(f"\nQuery Pattern Analysis:")
        for query_type, categories in pattern_results.items():
            print(f"  {query_type}: {len(categories)} categories")
            for category, stats in categories.items():
                print(f"    {category}: {stats['latency_avg_ms']}ms avg latency")

        return pattern_results

    async def generate_report(self, output_file: str = None):
        """Generate comprehensive benchmark report"""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"hybrid_search_benchmark_{timestamp}.json"

        print(f"\nGenerating benchmark report: {output_file}")

        # Add performance metrics summary
        self.results["performance_metrics"] = {
            "overall_grade": self._calculate_performance_grade(),
            "recommendations": self._generate_recommendations()
        }

        # Write report to file
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)

        print(f"Benchmark report saved to: {output_file}")
        return output_file

    def _calculate_performance_grade(self) -> str:
        """Calculate overall performance grade"""
        latency_analysis = self.results.get("latency_analysis", {})
        throughput_tests = self.results.get("throughput_tests", {})

        score = 100

        # Latency scoring
        if "target_compliance" in latency_analysis:
            if not latency_analysis["target_compliance"]["p95_under_200ms"]:
                score -= 30
            if not latency_analysis["target_compliance"]["average_under_150ms"]:
                score -= 20
            if not latency_analysis["target_compliance"]["max_under_400ms"]:
                score -= 10

        # Throughput scoring
        if "target_compliance" in throughput_tests:
            if not throughput_tests["target_compliance"]["achieved_10_qps"]:
                score -= 30
            if not throughput_tests["target_compliance"]["achieved_50_qps_single"]:
                score -= 10

        if score >= 90:
            return "A"
        elif score >= 80:
            return "B"
        elif score >= 70:
            return "C"
        elif score >= 60:
            return "D"
        else:
            return "F"

    def _generate_recommendations(self) -> List[str]:
        """Generate performance improvement recommendations"""
        recommendations = []

        latency_analysis = self.results.get("latency_analysis", {})
        throughput_tests = self.results.get("throughput_tests", {})

        # Latency recommendations
        if "target_compliance" in latency_analysis:
            if not latency_analysis["target_compliance"]["p95_under_200ms"]:
                recommendations.append("Consider optimizing query processing or increasing search timeout")
            if latency_analysis["overall"]["latency_avg_ms"] > 150:
                recommendations.append("High average latency - review indexing strategy and query optimization")

        # Throughput recommendations
        if "target_compliance" in throughput_tests:
            if not throughput_tests["target_compliance"]["achieved_10_qps"]:
                recommendations.append("Low throughput - consider connection pooling and caching")
            if throughput_tests["max_qps"] < 50:
                recommendations.append("Consider implementing query result caching for frequently asked questions")

        # General recommendations
        if not recommendations:
            recommendations.append("Performance is within target ranges - continue monitoring")

        return recommendations

    async def run_all_benchmarks(self, output_file: str = None):
        """Run complete benchmark suite"""
        print("="*80)
        print("HYBRID SEARCH PERFORMANCE BENCHMARK SUITE")
        print("="*80)
        print(f"Timestamp: {self.results['benchmark_info']['timestamp']}")
        print(f"Platform: {self.results['benchmark_info']['platform']}")
        print(f"Python: {self.results['benchmark_info']['python_version']}")
        print(f"CPU Cores: {self.results['benchmark_info']['cpu_count']}")
        print(f"Memory: {self.results['benchmark_info']['memory_total_gb']:.1f}GB")
        print("="*80)

        try:
            await self.setup()

            # Run all benchmarks
            await self.benchmark_latency()
            await self.benchmark_throughput()
            await self.benchmark_resource_utilization()
            await self.benchmark_query_patterns()

            # Generate report
            report_file = await self.generate_report(output_file)

            # Print summary
            grade = self._calculate_performance_grade()
            recommendations = self._generate_recommendations()

            print("\n" + "="*80)
            print("BENCHMARK SUMMARY")
            print("="*80)
            print(f"Overall Performance Grade: {grade}")
            print(f"Report File: {report_file}")

            if recommendations:
                print("\nRecommendations:")
                for i, rec in enumerate(recommendations, 1):
                    print(f"  {i}. {rec}")

        except Exception as e:
            print(f"Benchmark failed with error: {e}")
            import traceback
            traceback.print_exc()

        finally:
            await self.cleanup()


async def main():
    """Main function to run benchmarks"""
    benchmark = HybridSearchBenchmark()

    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description="Hybrid Search Performance Benchmark")
    parser.add_argument("--output", "-o", help="Output file for benchmark report")
    parser.add_argument("--latency-only", action="store_true", help="Run latency benchmarks only")
    parser.add_argument("--throughput-only", action="store_true", help="Run throughput benchmarks only")

    args = parser.parse_args()

    try:
        if args.latency_only:
            await benchmark.setup()
            await benchmark.benchmark_latency()
            await benchmark.generate_report(args.output)
        elif args.throughput_only:
            await benchmark.setup()
            await benchmark.benchmark_throughput()
            await benchmark.generate_report(args.output)
        else:
            await benchmark.run_all_benchmarks(args.output)
    except KeyboardInterrupt:
        print("\nBenchmark interrupted by user")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await benchmark.cleanup()


if __name__ == "__main__":
    asyncio.run(main())