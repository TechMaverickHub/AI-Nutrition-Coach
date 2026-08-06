"""Report service: render a weekly nutrition PDF from analytics data."""

import io
import uuid

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.schemas.analytics import AnalyticsRead
from app.services.analytics import AnalyticsService

_ACCENT = colors.HexColor("#157F55")
_HEADER_BG = colors.HexColor("#E4F1EA")
_GRID = colors.HexColor("#DDE4DC")


class ReportService:
    """Builds a downloadable weekly report PDF. Reuses the analytics data."""

    def __init__(self, analytics_service: AnalyticsService) -> None:
        self._analytics = analytics_service

    async def generate_weekly_pdf(self, user_id: uuid.UUID, email: str) -> bytes:
        analytics = await self._analytics.get_analytics(user_id, 7)
        return self._render(analytics, email)

    @staticmethod
    def _render(a: AnalyticsRead, email: str) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            title="Weekly Nutrition Report",
            author="AI Nutrition Coach",
            topMargin=20 * mm,
            bottomMargin=20 * mm,
            leftMargin=18 * mm,
            rightMargin=18 * mm,
        )
        styles = getSampleStyleSheet()
        elements: list[object] = []

        elements.append(Paragraph("Weekly Nutrition Report", styles["Title"]))
        elements.append(
            Paragraph(
                f"{email} &nbsp;·&nbsp; {a.start_date.isoformat()} to {a.end_date.isoformat()}",
                styles["Normal"],
            )
        )
        elements.append(Spacer(1, 8 * mm))

        # Summary
        s = a.summary
        on_target = "n/a" if s.days_on_target is None else f"{s.days_on_target} of {s.days_logged}"
        elements.append(Paragraph("Summary", styles["Heading2"]))
        summary_rows = [
            ["Average calories / day", str(s.avg_calories)],
            ["Average protein / day", f"{s.avg_protein} g"],
            ["Average carbs / day", f"{s.avg_carbs} g"],
            ["Average fat / day", f"{s.avg_fat} g"],
            ["Days logged", f"{s.days_logged} of 7"],
            ["Total meals", str(s.total_meals)],
            ["Days within calorie goal", on_target],
        ]
        summary_table = Table(summary_rows, colWidths=[70 * mm, 90 * mm])
        summary_table.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.5, _GRID),
                    ("BACKGROUND", (0, 0), (0, -1), _HEADER_BG),
                    ("TEXTCOLOR", (0, 0), (0, -1), _ACCENT),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        elements.append(summary_table)
        elements.append(Spacer(1, 6 * mm))

        if a.goal is not None:
            g = a.goal
            elements.append(
                Paragraph(
                    f"<b>Goal:</b> {g.daily_calories} kcal/day · protein {g.protein_goal} g · "
                    f"carbs {g.carb_goal} g · fat {g.fat_goal} g",
                    styles["Normal"],
                )
            )
            elements.append(Spacer(1, 6 * mm))

        # Daily breakdown
        elements.append(Paragraph("Daily breakdown", styles["Heading2"]))
        header = ["Date", "Calories", "Protein (g)", "Carbs (g)", "Fat (g)", "Meals"]
        daily_rows = [header] + [
            [
                p.date.isoformat(),
                str(p.calories),
                str(p.protein),
                str(p.carbs),
                str(p.fat),
                str(p.meal_count),
            ]
            for p in a.daily
        ]
        daily_table = Table(daily_rows, repeatRows=1)
        daily_table.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.5, _GRID),
                    ("BACKGROUND", (0, 0), (-1, 0), _ACCENT),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                    ("ALIGN", (0, 0), (0, -1), "LEFT"),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.HexColor("#F6F9F6")],
                    ),
                ]
            )
        )
        elements.append(daily_table)

        doc.build(elements)
        return buffer.getvalue()
