import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
import json


class PipelineLogger:
    """Comprehensive logging system for CleanMol pipeline runs."""

    def __init__(self, output_dir: str, config: Dict[str, Any], progress_callback: Callable[[str], None] = None):
        self.output_dir = Path(output_dir)
        self.logs_dir = self.output_dir / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        self.run_id = str(uuid.uuid4())
        self.started_at = datetime.now(timezone.utc)
        self.finished_at: Optional[datetime] = None

        self.config = config
        self.documents: List[Dict[str, Any]] = []
        self.current_doc: Optional[Dict[str, Any]] = None
        self.errors: List[Dict[str, Any]] = []
        self.warnings: List[Dict[str, Any]] = []
        self.api_calls: List[Dict[str, Any]] = []

        # Final extraction summary
        self.all_molecules: List[Dict[str, Any]] = []
        self.all_experiments: List[Dict[str, Any]] = []
        self.all_results: List[Dict[str, Any]] = []

        # Database stats
        self.db_stats: Dict[str, int] = {}

        # Progress callback for streaming updates
        self.progress_callback = progress_callback

        # Generate log filename
        timestamp = self.started_at.strftime("%Y-%m-%d_%H-%M-%S")
        self.log_filename = f"cleanmol_run_{timestamp}.md"
        self.log_path = self.logs_dir / self.log_filename

    def _utc_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).strftime("%H:%M:%S")

    def _emit(self, message: str):
        """Emit a progress message to the callback if set."""
        if self.progress_callback:
            try:
                self.progress_callback(message)
            except Exception:
                pass

    def emit_progress(self, stage: str, event: str, doc_index: int = 0, doc_total: int = 0, stats: dict = None):
        """Emit structured progress for frontend weighted progress bar."""
        if self.progress_callback:
            payload = {
                "type": "stage_progress",
                "stage": stage,
                "event": event,  # "start" or "end"
                "doc_index": doc_index,
                "doc_total": doc_total,
            }
            if stats:
                payload["stats"] = stats
            try:
                self.progress_callback(json.dumps(payload))
            except Exception:
                pass

    def start_document(self, filename: str, doc_id: str, path: str):
        """Start logging a new document."""
        self.current_doc = {
            "filename": filename,
            "doc_id": doc_id,
            "path": path,
            "status": "processing",
            "started_at": self._utc_iso(),
            "finished_at": None,
            "pages": 0,
            "stages": {},
            "errors": [],
            "warnings": []
        }
        self._emit(f"Starting document: {filename}")

    def set_document_pages(self, pages: int):
        """Set the page count for current document."""
        if self.current_doc:
            self.current_doc["pages"] = pages

    def end_document(self, status: str = "success"):
        """Finish logging current document."""
        if self.current_doc:
            self.current_doc["status"] = status
            self.current_doc["finished_at"] = self._utc_iso()
            filename = self.current_doc.get("filename", "unknown")
            self.documents.append(self.current_doc)
            self.current_doc = None
            self._emit(f"Document {filename} completed with status: {status}")

    def log_stage(self, stage_name: str, data: Dict[str, Any]):
        """Log a pipeline stage for the current document."""
        if self.current_doc:
            data["timestamp"] = self._utc_iso()
            self.current_doc["stages"][stage_name] = data
        status = data.get("status", "unknown")
        self._emit(f"[{stage_name}] {status}")

    def log_error(self, message: str, stage: str = "", doc_id: str = "", exception: Optional[Exception] = None):
        """Log an error."""
        error = {
            "timestamp": self._timestamp(),
            "doc_id": doc_id or (self.current_doc["doc_id"] if self.current_doc else ""),
            "stage": stage,
            "message": message,
            "exception": str(exception) if exception else None
        }
        self.errors.append(error)
        if self.current_doc:
            self.current_doc["errors"].append(error)
        self._emit(f"ERROR [{stage}]: {message}")

    def log_warning(self, message: str, stage: str = "", doc_id: str = ""):
        """Log a warning."""
        warning = {
            "timestamp": self._timestamp(),
            "doc_id": doc_id or (self.current_doc["doc_id"] if self.current_doc else ""),
            "stage": stage,
            "message": message
        }
        self.warnings.append(warning)
        if self.current_doc:
            self.current_doc["warnings"].append(warning)
        self._emit(f"WARNING [{stage}]: {message}")

    def log_api_call(self, provider: str, model: str, endpoint: str,
                     tokens_in: int, tokens_out: int, duration_sec: float,
                     status: str = "success"):
        """Log an API call."""
        self.api_calls.append({
            "timestamp": self._timestamp(),
            "provider": provider,
            "model": model,
            "endpoint": endpoint,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "duration_sec": round(duration_sec, 2),
            "status": status
        })
        self._emit(f"API: {provider} {model} ({tokens_in}â†’{tokens_out} tokens, {duration_sec:.1f}s)")

    def set_db_stats(self, stats: Dict[str, int]):
        """Set database statistics."""
        self.db_stats = stats

    def add_extraction_summary(self, molecules: List, experiments: List, results: List, doc_id: str):
        """Add extraction results to summary."""
        for m in molecules:
            m_copy = dict(m)
            m_copy["source_doc"] = doc_id
            self.all_molecules.append(m_copy)
        for e in experiments:
            e_copy = dict(e)
            e_copy["source_doc"] = doc_id
            self.all_experiments.append(e_copy)
        for r in results:
            r_copy = dict(r)
            r_copy["source_doc"] = doc_id
            self.all_results.append(r_copy)

    def finalize(self) -> str:
        """Finalize the log and write to file. Returns the log file path."""
        self.finished_at = datetime.now(timezone.utc)

        # Generate the markdown log
        md = self._generate_markdown()

        # Write to file
        self.log_path.write_text(md, encoding="utf-8")

        return str(self.log_path)

    def _generate_markdown(self) -> str:
        """Generate the full markdown log."""
        lines = []

        # Calculate duration
        duration = self.finished_at - self.started_at
        duration_min = int(duration.total_seconds() // 60)
        duration_sec = int(duration.total_seconds() % 60)

        # Determine overall status
        failed_docs = [d for d in self.documents if d["status"] == "failed"]
        if len(failed_docs) == len(self.documents) and len(self.documents) > 0:
            overall_status = "âŒ FAILED"
        elif len(failed_docs) > 0:
            overall_status = "âš ï¸ PARTIAL"
        elif len(self.errors) > 0:
            overall_status = "âš ï¸ COMPLETED WITH ERRORS"
        else:
            overall_status = "âœ… SUCCESS"

        # Header
        lines.append("# CleanMol Pipeline Run Log\n")

        # Run Summary
        lines.append("## Run Summary\n")
        lines.append(f"- **Run ID:** `{self.run_id}`")
        lines.append(f"- **Started:** {self.started_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        lines.append(f"- **Finished:** {self.finished_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        lines.append(f"- **Duration:** {duration_min}m {duration_sec}s")
        lines.append(f"- **Status:** {overall_status}")
        lines.append(f"- **Documents Processed:** {len(self.documents)}")
        lines.append(f"- **Documents Failed:** {len(failed_docs)}")
        lines.append(f"- **Total Errors:** {len(self.errors)}")
        lines.append(f"- **Total Warnings:** {len(self.warnings)}\n")

        # Configuration
        lines.append("## Configuration\n")
        lines.append(f"- **Input Directory:** `{self.config.get('input_dir', 'N/A')}`")
        lines.append(f"- **Output Directory:** `{self.config.get('output_dir', 'N/A')}`")
        models = self.config.get("models", {})
        lines.append(f"- **Primary Model:** `{models.get('primary', 'N/A')}`")
        lines.append(f"- **Auditor Model:** `{models.get('auditor', 'N/A')}`")
        lines.append(f"- **Gap Hunter Model:** `{models.get('gapHunter', 'N/A')}`")
        options = self.config.get("options", {})
        lines.append(f"- **Max Gap Rounds:** {options.get('max_gap_rounds', 2)}\n")

        # API Keys Status
        keys = self.config.get("keys", {})
        lines.append("## API Keys Status\n")
        lines.append(f"- **Anthropic:** {'âœ… Provided' if keys.get('anthropic') else 'âŒ Missing'}")
        lines.append(f"- **OpenAI:** {'âœ… Provided' if keys.get('openai') else 'âŒ Missing'}")
        lines.append(f"- **Google:** {'âœ… Provided' if keys.get('gemini') else 'âŒ Missing'}\n")

        lines.append("---\n")

        # Document Processing
        lines.append("## Document Processing\n")

        if not self.documents:
            lines.append("*No documents were processed.*\n")

        for i, doc in enumerate(self.documents, 1):
            status_icon = "âœ…" if doc["status"] == "success" else "âŒ"
            lines.append(f"### Document {i}: {doc['filename']}\n")
            lines.append(f"- **Doc ID:** `{doc['doc_id']}`")
            lines.append(f"- **Status:** {status_icon} {doc['status'].upper()}")
            lines.append(f"- **Pages:** {doc.get('pages', 'N/A')}")

            # Calculate processing time
            if doc.get("started_at") and doc.get("finished_at"):
                start = datetime.fromisoformat(doc["started_at"].replace("Z", "+00:00"))
                end = datetime.fromisoformat(doc["finished_at"].replace("Z", "+00:00"))
                proc_time = (end - start).total_seconds()
                lines.append(f"- **Processing Time:** {proc_time:.1f}s\n")
            else:
                lines.append(f"- **Processing Time:** N/A\n")

            # Stages
            stages = doc.get("stages", {})
            for stage_name, stage_data in stages.items():
                stage_status = stage_data.get("status", "unknown")
                if stage_status == "success":
                    status_icon = "âœ…"
                elif stage_status == "skipped":
                    status_icon = "â­ï¸"
                else:
                    status_icon = "âŒ"

                lines.append(f"#### {stage_name}")
                lines.append(f"- **Status:** {status_icon} {stage_status.upper()}")
                if stage_data.get("time"):
                    lines.append(f"- **Time:** {stage_data['time']:.1f}s")
                for key, value in stage_data.items():
                    if key not in ["status", "time", "timestamp"]:
                        if isinstance(value, dict):
                            lines.append(f"- **{key.replace('_', ' ').title()}:**")
                            for k, v in value.items():
                                lines.append(f"  - {k}: {v}")
                        else:
                            lines.append(f"- **{key.replace('_', ' ').title()}:** {value}")
                lines.append("")

            # Document Errors
            lines.append("#### Document Errors")
            if doc.get("errors"):
                for err in doc["errors"]:
                    lines.append(f"> âŒ [{err['stage']}] {err['message']}")
            else:
                lines.append("> None")
            lines.append("")

            # Document Warnings
            lines.append("#### Document Warnings")
            if doc.get("warnings"):
                for warn in doc["warnings"]:
                    lines.append(f"> âš ï¸ [{warn['stage']}] {warn['message']}")
            else:
                lines.append("> None")
            lines.append("")

            lines.append("---\n")

        # Errors and Warnings Summary
        lines.append("## Errors and Warnings Summary\n")

        lines.append("### Critical Errors\n")
        if self.errors:
            lines.append("| Time | Document | Stage | Error |")
            lines.append("|------|----------|-------|-------|")
            for err in self.errors:
                msg = err['message'].replace("|", "\\|")[:100]
                lines.append(f"| {err['timestamp']} | {err['doc_id']} | {err['stage']} | {msg} |")
        else:
            lines.append("*No errors occurred.*")
        lines.append("")

        lines.append("### Warnings\n")
        if self.warnings:
            lines.append("| Time | Document | Stage | Warning |")
            lines.append("|------|----------|-------|---------|")
            for warn in self.warnings:
                msg = warn['message'].replace("|", "\\|")[:100]
                lines.append(f"| {warn['timestamp']} | {warn['doc_id']} | {warn['stage']} | {msg} |")
        else:
            lines.append("*No warnings.*")
        lines.append("")

        lines.append("---\n")

        # API Call Log
        lines.append("## API Call Log\n")
        if self.api_calls:
            lines.append("| Time | Provider | Model | Endpoint | Tokens In | Tokens Out | Duration | Status |")
            lines.append("|------|----------|-------|----------|-----------|------------|----------|--------|")
            for call in self.api_calls:
                status_icon = "âœ…" if call["status"] == "success" else "âŒ"
                model_short = call['model'][:25] + "..." if len(call['model']) > 25 else call['model']
                lines.append(f"| {call['timestamp']} | {call['provider']} | {model_short} | {call['endpoint']} | {call['tokens_in']} | {call['tokens_out']} | {call['duration_sec']}s | {status_icon} |")
        else:
            lines.append("*No API calls logged.*")
        lines.append("")

        lines.append("---\n")

        # Final Extraction Summary
        lines.append("## Final Extraction Summary\n")

        lines.append("### Molecules\n")
        if self.all_molecules:
            lines.append("| molecule_id | name_as_written | head_group_class | source_doc |")
            lines.append("|-------------|-----------------|------------------|------------|")
            for m in self.all_molecules[:20]:  # Limit to first 20
                name = str(m.get('name_as_written', 'N/A'))[:30]
                lines.append(f"| {m.get('molecule_id', 'N/A')} | {name} | {m.get('head_group_class', 'N/A')} | {m.get('source_doc', 'N/A')} |")
            if len(self.all_molecules) > 20:
                lines.append(f"\n*... and {len(self.all_molecules) - 20} more molecules*")
        else:
            lines.append("*No molecules extracted.*")
        lines.append("")

        lines.append("### Experiments\n")
        if self.all_experiments:
            lines.append("| experiment_id | organism | assay_type | source_doc |")
            lines.append("|---------------|----------|------------|------------|")
            for e in self.all_experiments[:20]:
                lines.append(f"| {e.get('experiment_id', 'N/A')} | {e.get('organism', 'N/A')} | {e.get('assay_type', 'N/A')} | {e.get('source_doc', 'N/A')} |")
            if len(self.all_experiments) > 20:
                lines.append(f"\n*... and {len(self.all_experiments) - 20} more experiments*")
        else:
            lines.append("*No experiments extracted.*")
        lines.append("")

        lines.append("### Results\n")
        if self.all_results:
            lines.append("| result_id | molecule_id | experiment_id | endpoint | value | units | confidence |")
            lines.append("|-----------|-------------|---------------|----------|-------|-------|------------|")
            for r in self.all_results[:20]:
                lines.append(f"| {r.get('result_id', 'N/A')} | {r.get('molecule_id', 'N/A')} | {r.get('experiment_id', 'N/A')} | {r.get('endpoint', 'N/A')} | {r.get('value', 'N/A')} | {r.get('units', 'N/A')} | {r.get('confidence', 'N/A')} |")
            if len(self.all_results) > 20:
                lines.append(f"\n*... and {len(self.all_results) - 20} more results*")
        else:
            lines.append("*No results extracted.*")
        lines.append("")

        lines.append("---\n")

        # Database Statistics
        lines.append("## Database Statistics\n")
        lines.append(f"- **Total Molecules:** {self.db_stats.get('molecules', len(self.all_molecules))}")
        lines.append(f"- **Total Experiments:** {self.db_stats.get('experiments', len(self.all_experiments))}")
        lines.append(f"- **Total Results:** {self.db_stats.get('results', len(self.all_results))}")
        lines.append(f"- **Total Evidence Records:** {self.db_stats.get('evidence', 0)}")
        lines.append(f"- **Total Audits:** {self.db_stats.get('audits', 0)}")
        lines.append(f"- **Total Repairs:** {self.db_stats.get('repairs', 0)}")
        lines.append(f"- **Total Gap Suggestions:** {self.db_stats.get('gap_suggestions', 0)}\n")

        lines.append("---\n")

        # Recommendations
        lines.append("## Recommendations for Next Run\n")
        recommendations = self._generate_recommendations()
        if recommendations:
            for i, rec in enumerate(recommendations, 1):
                lines.append(f"{i}. {rec}")
        else:
            lines.append("*No specific recommendations. The run completed successfully.*")
        lines.append("")

        lines.append("---\n")

        # Raw Configuration
        lines.append("## Raw Configuration\n")
        lines.append("```json")
        # Mask API keys for security
        safe_config = dict(self.config)
        if "keys" in safe_config:
            safe_config["keys"] = {k: "***" if v else None for k, v in safe_config["keys"].items()}
        lines.append(json.dumps(safe_config, indent=2))
        lines.append("```\n")

        # Footer
        lines.append("---\n")
        lines.append("*Log generated by CleanMol v1.0*")
        lines.append("")
        lines.append('*For troubleshooting, provide this log to an LLM with the prompt: "Review this CleanMol pipeline log and identify any issues or suggest improvements."*')

        return "\n".join(lines)

    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on the run."""
        recs = []

        # Check for missing API keys
        keys = self.config.get("keys", {})
        if not keys.get("openai"):
            recs.append("Consider adding an OpenAI API key to enable audit verification.")
        if not keys.get("gemini"):
            recs.append("Consider adding a Google API key to enable Gemini gap hunting.")

        # Check for high error count
        if len(self.errors) > 5:
            recs.append(f"High error count ({len(self.errors)} errors). Review errors above and consider processing documents individually.")

        # Check for low confidence results
        low_confidence = [r for r in self.all_results if isinstance(r.get("confidence"), (int, float)) and r.get("confidence", 1.0) < 0.5]
        if low_confidence:
            recs.append(f"{len(low_confidence)} results have low confidence (< 0.5). Manual review recommended.")

        # Check for skipped stages
        for doc in self.documents:
            stages = doc.get("stages", {})
            skipped = [s for s, d in stages.items() if d.get("status") == "skipped"]
            if skipped:
                recs.append(f"Some stages were skipped for {doc['filename']}. Ensure all API keys are provided for full pipeline.")
                break

        # Check for no extractions
        if not self.all_molecules and not self.all_experiments and not self.all_results:
            recs.append("No data was extracted. Verify that the input PDFs contain relevant chemistry content.")

        # Check for failed documents
        failed_docs = [d for d in self.documents if d["status"] == "failed"]
        if failed_docs:
            recs.append(f"{len(failed_docs)} document(s) failed processing. Check the errors section for details.")

        return recs
