"""Generate comprehensive batch processing summary reports."""

from datetime import datetime
from pathlib import Path
from typing import Optional

from models import Invoice
from models.batch_result import BatchResult


class SummaryGenerator:
    """Generate markdown summary reports for batch processing runs."""

    def __init__(self, output_dir: Path):
        """
        Initialize summary generator.

        Args:
            output_dir: Directory to save summary file
        """
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_summary(
        self,
        batch_results: list[BatchResult],
        all_invoices: list[Invoice],
        processing_time: float,
        output_file: Optional[Path] = None,
    ) -> Path:
        """
        Generate comprehensive batch processing summary.

        Args:
            batch_results: List of BatchResult objects from all vendors
            all_invoices: Combined list of all successful invoices
            processing_time: Total processing time in seconds
            output_file: Optional custom output path

        Returns:
            Path to generated summary file
        """
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = self.output_dir / f"BATCH_SUMMARY_{timestamp}.md"

        # Calculate statistics
        stats = self._calculate_statistics(batch_results, all_invoices, processing_time)

        # Generate markdown content
        content = self._generate_markdown(stats)

        # Write to file
        with open(output_file, "w") as f:
            f.write(content)

        return output_file

    def _calculate_statistics(
        self, batch_results: list[BatchResult], all_invoices: list[Invoice], processing_time: float
    ) -> dict:
        """Calculate comprehensive statistics from batch results."""
        total_files = sum(r.statistics.total_files for r in batch_results)
        total_successful = sum(r.statistics.successful for r in batch_results)
        total_failed = sum(r.statistics.failed_total for r in batch_results)

        # Overall stats
        stats = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_files": total_files,
            "total_successful": total_successful,
            "total_failed": total_failed,
            "success_rate": (total_successful / total_files * 100) if total_files > 0 else 0,
            "processing_time": processing_time,
            "avg_time_per_file": (processing_time / total_files) if total_files > 0 else 0,
        }

        # Error and issue counts
        errors = []
        warnings = []
        for invoice in all_invoices:
            if invoice.extraction_errors:
                errors.extend(invoice.extraction_errors)
            if invoice.extraction_confidence < 0.8:
                warnings.append(
                    f"{invoice.source_file}: Low confidence ({invoice.extraction_confidence:.1%})"
                )

        stats["error_count"] = len(errors)
        stats["warning_count"] = len(warnings)
        stats["errors"] = errors[:10]  # Top 10 errors
        stats["warnings"] = warnings[:10]  # Top 10 warnings

        # Confidence distribution
        if all_invoices:
            confidence_levels = [inv.extraction_confidence for inv in all_invoices]
            stats["confidence"] = {
                "high": sum(1 for c in confidence_levels if c >= 0.9),
                "medium": sum(1 for c in confidence_levels if 0.7 <= c < 0.9),
                "low": sum(1 for c in confidence_levels if c < 0.7),
                "average": sum(confidence_levels) / len(confidence_levels),
            }
        else:
            stats["confidence"] = {"high": 0, "medium": 0, "low": 0, "average": 0.0}

        # Vendor performance
        vendor_stats = []
        for result in batch_results:
            vendor_invoices = [
                inv
                for inv in all_invoices
                if any(
                    inv.source_file == r.filename
                    for r in result.results
                    if r.status == "success"
                )
            ]

            if vendor_invoices:
                vendor_name = vendor_invoices[0].vendor
                total_amount = sum(inv.total for inv in vendor_invoices if inv.total)
                total_line_items = sum(len(inv.line_items) for inv in vendor_invoices)
                avg_confidence = (
                    sum(inv.extraction_confidence for inv in vendor_invoices)
                    / len(vendor_invoices)
                )

                vendor_stats.append(
                    {
                        "name": vendor_name,
                        "processed": result.statistics.successful,
                        "failed": result.statistics.failed_total,
                        "total_amount": total_amount,
                        "line_items": total_line_items,
                        "avg_confidence": avg_confidence,
                        "success_rate": (
                            result.statistics.successful / result.statistics.total_files * 100
                            if result.statistics.total_files > 0
                            else 0
                        ),
                    }
                )

        stats["vendors"] = sorted(vendor_stats, key=lambda x: x["processed"], reverse=True)

        # Financial summary
        stats["financial"] = {
            "total_invoice_amount": sum(inv.total for inv in all_invoices if inv.total),
            "total_line_items": sum(len(inv.line_items) for inv in all_invoices),
            "avg_invoice_amount": (
                sum(inv.total for inv in all_invoices if inv.total) / len(all_invoices)
                if all_invoices
                else 0
            ),
        }

        # Recommendations
        stats["recommendations"] = self._generate_recommendations(stats, all_invoices)

        return stats

    def _generate_recommendations(self, stats: dict, all_invoices: list[Invoice]) -> list[str]:
        """Generate recommendations based on processing results."""
        recommendations = []

        # Error rate check
        if stats["total_failed"] > 0:
            fail_rate = stats["total_failed"] / stats["total_files"] * 100
            if fail_rate > 10:
                recommendations.append(
                    f"⚠️ High failure rate ({fail_rate:.1f}%). Review failed extractions and improve vendor-specific patterns."
                )

        # Confidence check
        if stats["confidence"]["low"] > 0:
            low_pct = stats["confidence"]["low"] / len(all_invoices) * 100
            if low_pct > 15:
                recommendations.append(
                    f"⚠️ {low_pct:.1f}% of invoices have low confidence (<70%). Review extraction logic for these vendors."
                )

        # Missing data check
        missing_totals = sum(1 for inv in all_invoices if not inv.total or inv.total == 0)
        if missing_totals > 0:
            recommendations.append(
                f"⚠️ {missing_totals} invoices missing total amounts. Verify extraction patterns."
            )

        missing_line_items = sum(1 for inv in all_invoices if len(inv.line_items) == 0)
        if missing_line_items > 0:
            recommendations.append(
                f"⚠️ {missing_line_items} invoices missing line items. Review table extraction logic."
            )

        # Performance check
        if stats["avg_time_per_file"] > 10:
            recommendations.append(
                f"💡 Average processing time is {stats['avg_time_per_file']:.1f}s per file. Consider increasing worker count or optimizing extraction logic."
            )

        # Success recommendations
        if stats["success_rate"] >= 95 and stats["confidence"]["average"] >= 0.85:
            recommendations.append(
                "✅ Excellent extraction quality! System is performing well across vendors."
            )

        if not recommendations:
            recommendations.append("✅ Processing completed without major issues.")

        return recommendations

    def _generate_markdown(self, stats: dict) -> str:
        """Generate markdown content from statistics."""
        md = []

        # Header
        md.append("# Batch Processing Summary Report")
        md.append("")
        md.append(f"**Generated:** {stats['timestamp']}")
        md.append("")
        md.append("---")
        md.append("")

        # Overall Performance
        md.append("## 📊 Overall Performance")
        md.append("")
        md.append(f"- **Total Files Processed:** {stats['total_files']}")
        md.append(f"- **Successful:** {stats['total_successful']} ({stats['success_rate']:.1f}%)")
        md.append(f"- **Failed:** {stats['total_failed']}")
        md.append(
            f"- **Processing Time:** {stats['processing_time']:.1f}s ({stats['avg_time_per_file']:.2f}s per file)"
        )
        md.append("")

        # Errors and Issues
        md.append("### 🔍 Errors and Issues")
        md.append("")
        md.append(f"- **Extraction Errors:** {stats['error_count']}")
        md.append(f"- **Warnings:** {stats['warning_count']}")
        md.append("")

        if stats["errors"]:
            md.append("**Top Errors:**")
            for error in stats["errors"]:
                md.append(f"- {error}")
            md.append("")

        if stats["warnings"]:
            md.append("**Warnings:**")
            for warning in stats["warnings"]:
                md.append(f"- {warning}")
            md.append("")

        # Confidence Distribution
        md.append("## 📈 Confidence Distribution")
        md.append("")
        md.append("| Level | Count | Percentage |")
        md.append("|-------|-------|------------|")
        total = sum([stats["confidence"]["high"], stats["confidence"]["medium"], stats["confidence"]["low"]])
        if total > 0:
            md.append(
                f"| High (≥90%) | {stats['confidence']['high']} | {stats['confidence']['high']/total*100:.1f}% |"
            )
            md.append(
                f"| Medium (70-89%) | {stats['confidence']['medium']} | {stats['confidence']['medium']/total*100:.1f}% |"
            )
            md.append(
                f"| Low (<70%) | {stats['confidence']['low']} | {stats['confidence']['low']/total*100:.1f}% |"
            )
        md.append("")
        md.append(f"**Average Confidence:** {stats['confidence']['average']:.1%}")
        md.append("")

        # Vendor Performance
        md.append("## 🏢 Vendor Performance")
        md.append("")
        md.append("| Vendor | Processed | Failed | Success Rate | Line Items | Invoice Total | Avg Confidence |")
        md.append("|--------|-----------|--------|--------------|------------|---------------|----------------|")

        for vendor in stats["vendors"]:
            md.append(
                f"| {vendor['name']} | {vendor['processed']} | {vendor['failed']} | "
                f"{vendor['success_rate']:.1f}% | {vendor['line_items']} | "
                f"${vendor['total_amount']:,.2f} | {vendor['avg_confidence']:.1%} |"
            )
        md.append("")

        # Financial Summary
        md.append("## 💰 Financial Summary")
        md.append("")
        md.append(f"- **Total Invoice Amount:** ${stats['financial']['total_invoice_amount']:,.2f}")
        md.append(f"- **Total Line Items:** {stats['financial']['total_line_items']:,}")
        md.append(f"- **Average Invoice Amount:** ${stats['financial']['avg_invoice_amount']:,.2f}")
        md.append("")

        # Recommendations
        md.append("## 💡 Recommendations")
        md.append("")
        for rec in stats["recommendations"]:
            md.append(f"- {rec}")
        md.append("")

        md.append("---")
        md.append("")
        md.append("*Generated by documentExtraction batch processor*")

        return "\n".join(md)
