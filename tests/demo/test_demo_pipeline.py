"""Unit tests for demo pipeline main module."""

import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import pandas as pd

from acd.demo.pipeline import DemoPipeline


class TestDemoPipeline:
    """Test cases for DemoPipeline class."""

    def test_initialization(self):
        """Test DemoPipeline initialization."""
        pipeline = DemoPipeline(output_dir="test_outputs")

        assert pipeline.output_dir.name == "test_outputs"
        assert pipeline.ingestion is not None
        assert pipeline.feature_engineering is not None
        assert pipeline.config["window_size"] == 50
        assert pipeline.config["num_mock_windows"] == 3
        assert pipeline.config["enable_timestamping"] is True
        assert pipeline.config["enable_checksums"] is True

    def test_output_directory_creation(self):
        """Test output directory creation."""
        test_dir = "test_outputs_pipeline"

        # Clean up if exists
        if Path(test_dir).exists():
            import shutil

            shutil.rmtree(test_dir)

        pipeline = DemoPipeline(output_dir=test_dir)

        assert Path(test_dir).exists()
        assert Path(test_dir).is_dir()

        # Clean up
        import shutil

        shutil.rmtree(test_dir)

    @patch("acd.demo.pipeline.MockDataIngestion")
    @patch("acd.demo.pipeline.DemoFeatureEngineering")
    def test_run_full_pipeline_success(self, mock_feature_eng, mock_ingestion):
        """Test successful full pipeline execution."""
        pipeline = DemoPipeline()

        # Mock ingestion phase
        mock_ingestion_instance = MagicMock()
        mock_ingestion_instance.ingest_golden_datasets.return_value = {
            "competitive": 100,
            "coordinated": 100,
        }
        mock_ingestion_instance.generate_mock_feeds.return_value = [MagicMock(), MagicMock()]
        mock_ingestion_instance.validate_mock_data.return_value = {
            "completeness": 0.95,
            "accuracy": 0.90,
            "overall": 0.92,
        }
        mock_ingestion.return_value = mock_ingestion_instance

        # Mock feature engineering phase
        mock_feature_instance = MagicMock()
        mock_feature_instance.prepare_vmm_windows.return_value = [MagicMock(), MagicMock()]
        mock_feature_instance.run_vmm_analysis.return_value = MagicMock()
        mock_feature_instance.prepare_evidence_data.return_value = {
            "bundle_id": "test_bundle",
            "vmm_outputs": {"regime_confidence": 0.7, "structural_stability": 0.8},
        }
        mock_feature_eng.return_value = mock_feature_instance

        # Mock EvidenceBundle
        with patch("acd.demo.pipeline.EvidenceBundle") as mock_bundle_class:
            mock_bundle = MagicMock()
            mock_bundle.validate_schema.return_value = {"valid": True, "errors": []}
            mock_bundle_class.from_vmm_result.return_value = mock_bundle

            # Run pipeline
            results = pipeline.run_full_pipeline()

            # Check results
            assert results["success"] is True
            assert "start_time" in results
            assert "end_time" in results
            assert "execution_time" in results
            assert results["execution_time"] > 0

            # Check phases
            assert "ingestion_results" in results
            assert "feature_engineering_results" in results
            assert "evidence_bundles" in results
            assert "calibration_reports" in results
            assert "export_results" in results

    def test_run_full_pipeline_ingestion_failure(self):
        """Test pipeline failure during ingestion phase."""
        pipeline = DemoPipeline()

        # Mock ingestion failure on the instance
        with patch.object(
            pipeline.ingestion, "generate_mock_feeds", side_effect=Exception("Ingestion failed")
        ):
            # Run pipeline
            results = pipeline.run_full_pipeline()

            # Check failure
            assert results["success"] is False
            assert "errors" in results
            assert len(results["errors"]) > 0
            assert "Ingestion failed" in str(results["errors"][0])

    def test_run_ingestion_phase(self):
        """Test ingestion phase execution."""
        pipeline = DemoPipeline()

        # Mock ingestion methods
        with patch.object(pipeline.ingestion, "ingest_golden_datasets") as mock_golden:
            with patch.object(pipeline.ingestion, "generate_mock_feeds") as mock_feeds:
                with patch.object(pipeline.ingestion, "validate_mock_data") as mock_validate:

                    # Setup mocks
                    mock_golden.return_value = {"test_dataset": pd.DataFrame({"col": range(50)})}
                    mock_feeds.side_effect = [
                        [MagicMock(), MagicMock()],  # market_style
                        [MagicMock(), MagicMock()],  # regulatory_style
                    ]
                    mock_validate.return_value = {
                        "completeness": 0.95,
                        "accuracy": 0.90,
                        "overall": 0.92,
                    }

                    # Run ingestion phase
                    results = pipeline._run_ingestion_phase()

                    # Check results
                    assert "golden_datasets" in results
                    assert "mock_feeds" in results
                    assert "quality_metrics" in results

                    assert results["golden_datasets"]["test_dataset"] == 50
                    assert results["mock_feeds"]["market_style"] == 2
                    assert results["mock_feeds"]["regulatory_style"] == 2
                    assert len(results["quality_metrics"]) == 4  # 2 market + 2 regulatory

    def test_run_feature_engineering_phase(self):
        """Test feature engineering phase execution."""
        pipeline = DemoPipeline()

        # Mock ingestion results
        ingestion_results = {
            "mock_feeds": {"market_style": 2, "regulatory_style": 2},
            "quality_metrics": {"market_feed_0": {"overall": 0.9}},
        }

        # Mock feature engineering methods
        with patch.object(pipeline.feature_engineering, "prepare_vmm_windows") as mock_windows:
            with patch.object(pipeline.feature_engineering, "run_vmm_analysis") as mock_vmm:
                with patch.object(
                    pipeline.feature_engineering, "prepare_evidence_data"
                ) as mock_evidence:
                    with patch.object(pipeline.ingestion, "validate_mock_data") as mock_validate:

                        # Setup mocks
                        mock_windows.return_value = [MagicMock(), MagicMock()]
                        mock_vmm.return_value = MagicMock()
                        mock_evidence.return_value = {"bundle_id": "test_bundle"}
                        mock_validate.return_value = {"overall": 0.9}

                        # Run feature engineering phase
                        results = pipeline._run_feature_engineering_phase(ingestion_results)

                        # Check results
                        assert "vmm_windows" in results
                        assert "vmm_results" in results
                        assert "evidence_data" in results

                        # Should have 2 windows per market feed
                        assert len(results["vmm_windows"]) == 4  # 2 feeds * 2 windows
                        assert len(results["vmm_results"]) == 4
                        assert len(results["evidence_data"]) == 4

    def test_run_evidence_generation_phase(self):
        """Test evidence generation phase execution."""
        pipeline = DemoPipeline()

        # Mock feature results
        feature_results = {
            "evidence_data": [
                {"bundle_id": "bundle_1", "vmm_outputs": {"regime_confidence": 0.7}},
                {"bundle_id": "bundle_2", "vmm_outputs": {"regime_confidence": 0.8}},
            ]
        }

        # Mock EvidenceBundle
        with patch("acd.demo.pipeline.EvidenceBundle") as mock_bundle_class:
            mock_bundle = MagicMock()
            mock_bundle.validate_schema.return_value = {"valid": True, "errors": []}
            mock_bundle.bundle_id = "test_bundle"
            mock_bundle.creation_timestamp = "2024-01-01T00:00:00"
            mock_bundle.vmm_outputs.regime_confidence = 0.7
            mock_bundle.vmm_outputs.structural_stability = 0.8
            mock_bundle_class.from_vmm_result.return_value = mock_bundle

            # Run evidence generation phase
            results = pipeline._run_evidence_generation_phase(feature_results)

            # Check results
            assert "bundles" in results
            assert "reports" in results

            assert len(results["bundles"]) == 2
            assert len(results["reports"]) == 2

            # Check bundle data
            for bundle in results["bundles"]:
                assert "bundle_id" in bundle
                assert "creation_timestamp" in bundle
                assert "vmm_outputs" in bundle
                assert "validation" in bundle

    def test_run_export_phase(self):
        """Test export phase execution."""
        pipeline = DemoPipeline()

        # Mock evidence results
        evidence_results = {
            "bundles": [
                {"bundle_id": "bundle_1", "vmm_outputs": {"regime_confidence": 0.7}},
                {"bundle_id": "bundle_2", "vmm_outputs": {"regime_confidence": 0.8}},
            ],
            "reports": [{"timestamp": "2024-01-01T00:00:00", "content": "test_report"}],
        }

        # Mock EvidenceBundle for export
        with patch("acd.demo.pipeline.EvidenceBundle") as mock_bundle_class:
            mock_bundle = MagicMock()
            mock_bundle.bundle_id = "test_bundle"
            mock_bundle_class.from_vmm_result.return_value = mock_bundle

            # Mock file operations
            with patch("builtins.open", create=True) as mock_open:
                with patch("pathlib.Path.stat") as mock_stat:
                    mock_stat.return_value = MagicMock(st_size=1024)

                    # Run export phase
                    results = pipeline._run_export_phase(evidence_results)

                    # Check results
                    assert "exported_bundles" in results
                    assert "export_errors" in results

                    # Should have exported bundles and reports
                    assert len(results["exported_bundles"]) == 3  # 2 bundles + 1 report
                    assert len(results["export_errors"]) == 0

    def test_generate_calibration_report(self):
        """Test calibration report generation."""
        pipeline = DemoPipeline()

        # Mock bundle
        mock_bundle = MagicMock()
        mock_bundle.bundle_id = "test_bundle"
        mock_bundle.vmm_outputs.regime_confidence = 0.7
        mock_bundle.vmm_outputs.structural_stability = 0.8
        mock_bundle.vmm_outputs.dynamic_validation_score = 0.6
        mock_bundle.data_quality.overall_quality_score = 0.9
        mock_bundle.data_quality.completeness_score = 0.95
        mock_bundle.get_calibration_summary.return_value = {"method": "test", "score": 0.8}

        # Generate report
        report = pipeline._generate_calibration_report(mock_bundle)

        # Check report structure
        assert "timestamp" in report
        assert "bundle_id" in report
        assert "calibration_summary" in report
        assert "vmm_performance" in report
        assert "data_quality_summary" in report
        assert "validation_status" in report
        assert "recommendations" in report

        # Check content
        assert report["bundle_id"] == "test_bundle"
        assert report["vmm_performance"]["regime_confidence"] == 0.7
        assert report["vmm_performance"]["structural_stability"] == 0.8
        assert report["data_quality_summary"]["overall_score"] == 0.9

    def test_generate_pipeline_summary_success(self):
        """Test pipeline summary generation for successful execution."""
        pipeline = DemoPipeline()

        # Mock successful results
        results = {
            "success": True,
            "execution_time": 5.5,
            "start_time": "2024-01-01T00:00:00",
            "end_time": "2024-01-01T00:00:05",
            "ingestion_results": {
                "golden_datasets": {"competitive": 100},
                "mock_feeds": {"market_style": 2, "regulatory_style": 2},
                "quality_metrics": {"feed_1": {"overall": 0.9}},
            },
            "feature_engineering_results": {
                "vmm_windows": [{"id": "w1"}, {"id": "w2"}],
                "vmm_results": [{"conf": 0.7}, {"conf": 0.8}],
            },
            "evidence_bundles": [{"id": "b1"}, {"id": "b2"}],
            "calibration_reports": [{"id": "r1"}],
            "export_results": {
                "exported_bundles": [{"id": "e1"}, {"id": "e2"}],
                "export_errors": [],
            },
        }

        summary = pipeline.generate_pipeline_summary(results)

        # Check summary content
        assert "ACD Monitor Demo Pipeline" in summary
        assert "Execution Time: 5.5" in summary
        assert "Pipeline Status: SUCCESS" in summary
        assert "Golden Datasets: 1" in summary
        assert "Mock Feeds: 4" in summary
        assert "VMM Windows: 2" in summary
        assert "Evidence Bundles: 2" in summary

    def test_generate_pipeline_summary_failure(self):
        """Test pipeline summary generation for failed execution."""
        pipeline = DemoPipeline()

        # Mock failed results
        results = {"success": False, "execution_time": 2.1, "errors": ["Test error occurred"]}

        summary = pipeline.generate_pipeline_summary(results)

        # Check failure summary
        assert "❌ Pipeline failed after 2.1" in summary
