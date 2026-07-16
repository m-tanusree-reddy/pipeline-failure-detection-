"""
Pipeline Orchestration module for automated CI/CD pipeline failure investigation.
Connects log parsing, classification, retrieval, embedding, FAISS database, 
LLM analysis, Critic verification, and report generation in a unified workflow.
"""

import logging
import os
import sys
import time
from typing import List, Dict, Any, Optional

# Add project root directory to path to enable consistent imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

# Configure logging
logger = logging.getLogger(__name__)

# Import existing modules
from backend.log_parser import parse_log as _parse_log, load_log as _load_log
from backend.classifier import generate_classification as _generate_classification
from backend.agents.planner import generate_retrieval_plan as _generate_retrieval_plan
from backend.retrieval.collector import collect_documents as _collect_documents
from backend.retrieval.chunker import chunk_documents as _chunk_documents
from backend.retrieval.embedder import Embedder
from backend.retrieval.vector_store import VectorStore
from backend.retrieval.retriever import Retriever
from backend.services.llm_service import LLMService
from backend.agents.critic import CriticAgent
from backend.reporting.report_generator import ReportGenerator


class PipelineStageError(Exception):
    """
    Exception raised when a specific stage of the pipeline fails.
    """
    def __init__(self, stage_name: str, exception: Exception):
        self.stage_name = stage_name
        self.exception = exception
        super().__init__(f"Pipeline stage '{stage_name}' failed: {exception}")


class ParsedLog:
    """
    Wrapper class to allow both key and attribute access to parsed log dictionary.
    Exposes error_message and raw_log attributes expected by downstream pipeline stages.
    """
    def __init__(self, data: Dict[str, Any], raw_log_content: str):
        self._data = data
        self.raw_log = raw_log_content

    @property
    def error_message(self) -> str:
        return self._data.get("error_message", "")

    def __getattr__(self, name: str) -> Any:
        if name in self._data:
            return self._data[name]
        raise AttributeError(f"'ParsedLog' object has no attribute '{name}'")

    def __getitem__(self, item: str) -> Any:
        return self._data[item]

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def items(self):
        return self._data.items()


# Wrapper classes for function-based modules to support constructor initialization
class LogParser:
    """Wrapper for log parsing functions."""
    def parse_log(self, log_path: str) -> ParsedLog:
        raw_content = _load_log(log_path)
        data = _parse_log(log_path)
        return ParsedLog(data, raw_content)


class Classifier:
    """Wrapper for failure classification functions."""
    def generate_classification(self, parsed_log: ParsedLog) -> Dict[str, Any]:
        return _generate_classification(parsed_log)


class Planner:
    """Wrapper for retrieval planning functions."""
    def generate_retrieval_plan(self, classification: Dict[str, Any]):
        return _generate_retrieval_plan(classification)


class Collector:
    """Wrapper for document collection functions."""
    def collect(self, plan):
        return _collect_documents(plan)


class Chunker:
    """Wrapper for document chunking functions."""
    def chunk(self, documents):
        return _chunk_documents(documents)


class PipelineOrchestrator:
    """
    Orchestrates the execution of all system modules to investigate pipeline failures.
    Tracks execution status and performance metrics for each stage.
    """

    def __init__(self):
        """
        Initializes and links all modules.
        """
        # Function-based wrappers
        self.log_parser = LogParser()
        self.classifier = Classifier()
        self.planner = Planner()
        self.collector = Collector()
        self.chunker = Chunker()

        # Class-based instances
        self.embedder = Embedder()
        # Map expected method name 'embed' to 'embed_chunks'
        self.embedder.embed = self.embedder.embed_chunks

        self.vector_store = VectorStore()
        # Map expected method name 'build' to 'build_index'
        self.vector_store.build = self.vector_store.build_index

        self.retriever = Retriever()

        self.llm_service = LLMService()
        # Map expected method name 'analyze' to 'analyze_failure'
        self.llm_service.analyze = self.llm_service.analyze_failure

        self.critic = CriticAgent()
        # Map expected method name 'review' to 'evaluate'
        self.critic.review = self.critic.evaluate

        self.report_generator = ReportGenerator()
        # Map expected method name 'generate' to 'generate_report'
        self.report_generator.generate = self.report_generator.generate_report

        # Dict to track stage stats
        self.stage_stats: Dict[str, Dict[str, Any]] = {}

    def _execute_stage(self, stage_name: str, func, *args, **kwargs) -> Any:
        """
        Executes a pipeline stage, logs starts/ends, measures time, and handles errors.
        """
        logger.info(f"[{stage_name}] START")
        start_time = time.time()
        self.stage_stats[stage_name] = {"status": "FAILED", "time": 0.0}

        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            self.stage_stats[stage_name] = {"status": "SUCCESS", "time": duration}
            logger.info(f"[{stage_name}] END: Completed in {duration:.2f} sec")
            return result
        except Exception as e:
            duration = time.time() - start_time
            self.stage_stats[stage_name] = {"status": "FAILED", "time": duration}
            logger.error(f"[{stage_name}] FAILED in {duration:.2f} sec: {e}")
            raise PipelineStageError(stage_name, e)

    def run(self, log_path: str):
        """
        Runs the failure investigation pipeline from raw log to final report.

        Args:
            log_path: Path to the log file.

        Returns:
            PipelineFailureReport: The generated failure investigation report.
        """
        # Reset stats
        self.stage_stats = {}

        # STEP 1: Parse the log
        parsed_log = self._execute_stage("Parser", self.log_parser.parse_log, log_path)
        logger.info("Parsing completed.")

        # STEP 2: Generate classification
        classification = self._execute_stage("Classifier", self.classifier.generate_classification, parsed_log)
        logger.info("Classification completed.")

        # STEP 3: Generate retrieval plan
        plan = self._execute_stage("Planner", self.planner.generate_retrieval_plan, classification)
        logger.info("Retrieval plan generated.")

        # STEP 4: Collect documents
        documents = self._execute_stage("Collector", self.collector.collect, plan)
        logger.info(f"Collected {len(documents)} documents.")

        # STEP 5: Chunk documents
        chunks = self._execute_stage("Chunker", self.chunker.chunk, documents)
        logger.info(f"Generated {len(chunks)} chunks.")

        # STEP 6: Generate embeddings
        embedded_chunks = self._execute_stage("Embedder", self.embedder.embed, chunks)

        # STEP 7: Build FAISS index
        def build_and_save_index(chunks):
            self.vector_store.build(chunks)
            self.vector_store.save_index()
            self.vector_store.save_metadata()
            
        self._execute_stage("Vector Store", build_and_save_index, embedded_chunks)

        # STEP 8: Retrieve Top-K documents
        retrieved_documents = self._execute_stage(
            "Retriever", 
            self.retriever.retrieve,
            query=parsed_log.error_message,
            top_k=plan.top_k
        )
        logger.info(f"Retrieved {len(retrieved_documents)} documents.")

        # STEP 9: LLM Analysis
        analysis = self._execute_stage(
            "LLM", 
            self.llm_service.analyze,
            pipeline_error=parsed_log.error_message,
            retrieved_documents=retrieved_documents
        )

        # STEP 10: Critic
        critic_result = self._execute_stage(
            "Critic", 
            self.critic.review,
            analysis=analysis,
            retrieved_documents=retrieved_documents
        )

        # STEP 11: Generate Report
        report = self._execute_stage(
            "Report", 
            self.report_generator.generate,
            pipeline_error=parsed_log.raw_log,
            analysis=analysis,
            critic=critic_result,
            retrieved_documents=retrieved_documents
        )

        return report


if __name__ == "__main__":
    # Configure logging for console execution
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    # Locate Django sample log relative to the script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    django_log_path = os.path.join(
        script_dir, 
        "sample_logs", 
        "django_failure", 
        "0_Run Quality Checks on a PR.txt"
    )

    if not os.path.exists(django_log_path):
        print(f"Error: Sample log not found at expected path: {django_log_path}")
        sys.exit(1)

    orchestrator = PipelineOrchestrator()
    
    print("\nStarting CI/CD Failure Pipeline Orchestration...")
    try:
        report = orchestrator.run(django_log_path)
        
        # Print Summary Table
        print("\n================================")
        print("PIPELINE EXECUTION SUMMARY")
        print("================================")
        print(f"{'Stage':<15} {'Status':<10} {'Execution Time':<15}")
        print("--------------------------------")
        for stage in [
            "Parser", "Classifier", "Planner", "Collector", "Chunker", 
            "Embedder", "Vector Store", "Retriever", "LLM", "Critic", "Report"
        ]:
            stats = orchestrator.stage_stats.get(stage, {"status": "SKIPPED", "time": 0.0})
            print(f"{stage:<15} {stats['status']:<10} {stats['time']:.2f} sec")
        print("================================\n")

        # Print Final Report text
        print(report.to_text())

    except Exception as err:
        print(f"\nPipeline execution failed: {err}")
        # Print stats accumulated so far
        print("\n================================")
        print("PIPELINE EXECUTION SUMMARY (PARTIAL)")
        print("================================")
        print(f"{'Stage':<15} {'Status':<10} {'Execution Time':<15}")
        print("--------------------------------")
        for stage in [
            "Parser", "Classifier", "Planner", "Collector", "Chunker", 
            "Embedder", "Vector Store", "Retriever", "LLM", "Critic", "Report"
        ]:
            stats = orchestrator.stage_stats.get(stage, {"status": "SKIPPED", "time": 0.0})
            print(f"{stage:<15} {stats['status']:<10} {stats['time']:.2f} sec")
        print("================================\n")
