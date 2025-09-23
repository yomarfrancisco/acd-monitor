"""
ACD Artifact Loader

This module provides functionality to load and parse ACD analysis artifacts
from various storage locations for agent consumption.
"""

import json
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import logging

logger = logging.getLogger(__name__)


class ACDArtifactLoader:
    """
    Loads ACD analysis artifacts from storage locations

    This class provides methods to load various types of ACD artifacts
    including VMM provenance, validation results, and analysis reports.
    """

    def __init__(self, artifacts_dir: str = "artifacts"):
        self.artifacts_dir = Path(artifacts_dir)
        self.cache = {}  # Simple in-memory cache

        logger.info(f"ACDArtifactLoader initialized with artifacts_dir: {self.artifacts_dir}")

    def load_vmm_provenance(self, seed: int) -> Optional[Dict[str, Any]]:
        """
        Load VMM provenance data for a specific seed

        Args:
            seed: Random seed used for analysis

        Returns:
            VMM provenance data or None if not found
        """
        try:
            provenance_file = self.artifacts_dir / "vmm" / f"seed-{seed}" / "provenance.json"

            if not provenance_file.exists():
                logger.warning(f"VMM provenance not found for seed {seed}")
                return None

            with open(provenance_file, "r") as f:
                data = json.load(f)

            logger.info(f"Loaded VMM provenance for seed {seed}")
            return data

        except Exception as e:
            logger.error(f"Error loading VMM provenance for seed {seed}: {e}")
            return None

    def load_validation_results(
        self, analysis_type: str, seed: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Load validation results for a specific analysis type

        Args:
            analysis_type: Type of validation (lead_lag, mirroring, hmm, infoflow)
            seed: Optional seed to filter results

        Returns:
            Validation results or None if not found
        """
        try:
            # Look for validation files
            pattern = f"**/*{analysis_type}*"
            if seed:
                pattern = f"**/*seed*{seed}*{analysis_type}*"

            validation_files = list(self.artifacts_dir.glob(pattern))

            if not validation_files:
                logger.warning(f"No validation files found for {analysis_type}")
                return None

            # Load the most recent file
            latest_file = max(validation_files, key=lambda f: f.stat().st_mtime)

            with open(latest_file, "r") as f:
                data = json.load(f)

            logger.info(f"Loaded validation results for {analysis_type} from {latest_file}")
            return data

        except Exception as e:
            logger.error(f"Error loading validation results for {analysis_type}: {e}")
            return None

    def load_analysis_report(
        self, report_type: str, seed: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Load analysis report for a specific type

        Args:
            report_type: Type of report (atp, synthetic, integrated)
            seed: Optional seed to filter results

        Returns:
            Analysis report or None if not found
        """
        try:
            # Look for report files
            pattern = f"**/*{report_type}*report*"
            if seed:
                pattern = f"**/*{report_type}*seed*{seed}*"

            report_files = list(self.artifacts_dir.glob(pattern))

            if not report_files:
                logger.warning(f"No report files found for {report_type}")
                return None

            # Load the most recent file
            latest_file = max(report_files, key=lambda f: f.stat().st_mtime)

            with open(latest_file, "r") as f:
                data = json.load(f)

            logger.info(f"Loaded analysis report for {report_type} from {latest_file}")
            return data

        except Exception as e:
            logger.error(f"Error loading analysis report for {report_type}: {e}")
            return None

    def load_integrated_results(self, seed: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Load integrated analysis results

        Args:
            seed: Optional seed to filter results

        Returns:
            Integrated results or None if not found
        """
        try:
            # Look for integrated analysis files
            pattern = "**/*integrated*"
            if seed:
                pattern = f"**/*integrated*seed*{seed}*"

            integrated_files = list(self.artifacts_dir.glob(pattern))

            if not integrated_files:
                logger.warning("No integrated analysis files found")
                return None

            # Load the most recent file
            latest_file = max(integrated_files, key=lambda f: f.stat().st_mtime)

            with open(latest_file, "r") as f:
                data = json.load(f)

            logger.info(f"Loaded integrated results from {latest_file}")
            return data

        except Exception as e:
            logger.error(f"Error loading integrated results: {e}")
            return None

    def load_atp_case_results(self, seed: int = 42) -> Optional[Dict[str, Any]]:
        """
        Load ATP case study results

        Args:
            seed: Random seed used for ATP analysis

        Returns:
            ATP case results or None if not found
        """
        try:
            atp_dir = Path("cases/atp/artifacts")
            atp_file = atp_dir / f"atp_analysis_results_seed_{seed}.json"

            if not atp_file.exists():
                logger.warning(f"ATP case results not found for seed {seed}")
                return None

            with open(atp_file, "r") as f:
                data = json.load(f)

            logger.info(f"Loaded ATP case results for seed {seed}")
            return data

        except Exception as e:
            logger.error(f"Error loading ATP case results for seed {seed}: {e}")
            return None

    def list_available_artifacts(self) -> Dict[str, List[str]]:
        """
        List all available artifacts by type

        Returns:
            Dictionary mapping artifact types to file paths
        """
        artifacts = {
            "vmm_provenance": [],
            "validation_results": [],
            "analysis_reports": [],
            "integrated_results": [],
            "atp_case": [],
        }

        try:
            # VMM provenance
            vmm_dir = self.artifacts_dir / "vmm"
            if vmm_dir.exists():
                for seed_dir in vmm_dir.glob("seed-*"):
                    provenance_file = seed_dir / "provenance.json"
                    if provenance_file.exists():
                        artifacts["vmm_provenance"].append(str(provenance_file))

            # Validation results
            for validation_file in self.artifacts_dir.glob("**/*validation*"):
                if validation_file.suffix == ".json":
                    artifacts["validation_results"].append(str(validation_file))

            # Analysis reports
            for report_file in self.artifacts_dir.glob("**/*report*"):
                if report_file.suffix == ".json":
                    artifacts["analysis_reports"].append(str(report_file))

            # Integrated results
            for integrated_file in self.artifacts_dir.glob("**/*integrated*"):
                if integrated_file.suffix == ".json":
                    artifacts["integrated_results"].append(str(integrated_file))

            # ATP case
            atp_dir = Path("cases/atp/artifacts")
            if atp_dir.exists():
                for atp_file in atp_dir.glob("*.json"):
                    artifacts["atp_case"].append(str(atp_file))

        except Exception as e:
            logger.error(f"Error listing artifacts: {e}")

        return artifacts

    def get_artifact_metadata(self, file_path: str) -> Dict[str, Any]:
        """
        Get metadata for a specific artifact file

        Args:
            file_path: Path to artifact file

        Returns:
            Metadata dictionary
        """
        try:
            file_path_obj = Path(file_path)

            if not file_path_obj.exists():
                return {"error": "File not found"}

            stat = file_path_obj.stat()

            metadata = {
                "file_path": str(file_path_obj),
                "file_size": stat.st_size,
                "modified_time": stat.st_mtime,
                "file_type": file_path_obj.suffix,
                "parent_dir": str(file_path_obj.parent),
            }

            # Try to load and get basic info from JSON
            if file_path_obj.suffix == ".json":
                try:
                    with open(file_path_obj, "r") as f:
                        data = json.load(f)

                    if isinstance(data, dict):
                        metadata["keys"] = list(data.keys())
                        metadata["data_type"] = "json_object"
                    elif isinstance(data, list):
                        metadata["length"] = len(data)
                        metadata["data_type"] = "json_array"

                except Exception as e:
                    metadata["json_error"] = str(e)

            return metadata

        except Exception as e:
            logger.error(f"Error getting metadata for {file_path}: {e}")
            return {"error": str(e)}

    def search_artifacts(
        self, query: str, artifact_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search artifacts by content or metadata

        Args:
            query: Search query
            artifact_types: Optional list of artifact types to search

        Returns:
            List of matching artifacts with metadata
        """
        results = []

        try:
            available_artifacts = self.list_available_artifacts()

            # Filter by artifact types if specified
            if artifact_types:
                filtered_artifacts = {}
                for artifact_type in artifact_types:
                    if artifact_type in available_artifacts:
                        filtered_artifacts[artifact_type] = available_artifacts[artifact_type]
                available_artifacts = filtered_artifacts

            # Search through artifacts
            for artifact_type, file_paths in available_artifacts.items():
                for file_path in file_paths:
                    try:
                        # Search in file content
                        if self._search_in_file(file_path, query):
                            metadata = self.get_artifact_metadata(file_path)
                            metadata["artifact_type"] = artifact_type
                            metadata["match_reason"] = "content_match"
                            results.append(metadata)

                        # Search in file path
                        elif query.lower() in file_path.lower():
                            metadata = self.get_artifact_metadata(file_path)
                            metadata["artifact_type"] = artifact_type
                            metadata["match_reason"] = "path_match"
                            results.append(metadata)

                    except Exception as e:
                        logger.warning(f"Error searching in {file_path}: {e}")

        except Exception as e:
            logger.error(f"Error searching artifacts: {e}")

        return results

    def _search_in_file(self, file_path: str, query: str) -> bool:
        """
        Search for query in file content

        Args:
            file_path: Path to file
            query: Search query

        Returns:
            True if query found in file
        """
        try:
            file_path_obj = Path(file_path)

            if file_path_obj.suffix == ".json":
                with open(file_path_obj, "r") as f:
                    content = f.read()
                return query.lower() in content.lower()

            return False

        except Exception as e:
            logger.warning(f"Error searching in file {file_path}: {e}")
            return False
