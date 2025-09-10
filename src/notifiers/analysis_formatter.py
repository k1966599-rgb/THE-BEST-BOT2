from typing import List, Dict, Any
import uuid

# Use a try-except block for robust importing
try:
    from src.analysis.models import AnalysisReport, TimeframeAnalysis
except ImportError:
    # This allows the file to be potentially used in different contexts
    from analysis.models import AnalysisReport, TimeframeAnalysis


def format_timeframe_message(timeframe_analysis: TimeframeAnalysis, pair: str) -> str:
    """Formats a single timeframe analysis into a string message, using Markdown for style."""
    supports_str = "\n".join([f"`-` {s.type}: *{s.level}$* ({s.strength})" for s in timeframe_analysis.supports])
    resistances_str = "\n".join([f"`-` {r.type}: *{r.level}$* ({r.strength})" for r in timeframe_analysis.resistances])

    message = f"""
*🕐 فريم {timeframe_analysis.timeframe} — {pair}*
السعر الحالي: *{timeframe_analysis.current_price}$*

*📊 النموذج الفني: {timeframe_analysis.pattern.name} ({timeframe_analysis.pattern.status})*
*شروط التفعيل:* {timeframe_analysis.pattern.activation_condition}
*شروط الإلغاء:* {timeframe_analysis.pattern.invalidation_condition}

*🟢 الدعوم*
{supports_str}

*🔴 المقاومات*
{resistances_str}
"""
    return message.strip()

def format_summary_message(report: AnalysisReport) -> str:
    """Formats the summary and trade plan into a final message."""
    summary = report.summary
    trade = report.confirmed_trade

    # Ensure objects exist before formatting
    if not summary or not trade:
        return "الملخص غير متوفر."

    summary_str = f"""
*📌 الملخص التنفيذي والشامل*
*قصير المدى:* {summary.short_term_summary}
*متوسط المدى:* {summary.medium_term_summary}
*طويل المدى:* {summary.long_term_summary}

*نقاط المراقبة الحرجة:*
{summary.critical_points.get('resistance_breakout', 'N/A')}
{summary.critical_points.get('support_breakdown', 'N/A')}
"""

    trade_str = f"""
*📌 صفقة مؤكدة بعد دمج الفريمات الثلاثة*
*سعر الدخول المبدئي:* {trade.entry_price_condition}
*الأهداف:* {' → '.join(map(str, trade.targets))}$
*وقف الخسارة:* {trade.stop_loss_condition}
*استراتيجية دعم الفريمات:*
{trade.strategy_details}
"""

    return f"{summary_str.strip()}\n\n{trade_str.strip()}"


def format_full_analysis_messages(report: AnalysisReport) -> Dict[str, Any]:
    """
    Splits the full analysis report into multiple message parts for sending.
    The first message includes a general header.
    """
    if not report.report_id:
        report.report_id = str(uuid.uuid4())

    header = f"""
💎 *تحليل فني شامل - {report.pair}* 💎

*المنصة:* {report.platform}
*التاريخ والوقت:* {report.timestamp.strftime('%Y-%m-%d | %H:%M:%S')}
*السعر الحالي:* {report.timeframe_analyses[0].current_price}$
*نوع التحليل:* {report.analysis_type}
    """.strip()

    timeframe_messages = [
        format_timeframe_message(tf, report.pair) for tf in report.timeframe_analyses
    ]

    # Prepend the header to the first timeframe message
    if timeframe_messages:
        timeframe_messages[0] = f"{header}\n\n{timeframe_messages[0]}"

    summary_message = format_summary_message(report)

    return {
        "timeframe_messages": timeframe_messages,
        "summary_message": summary_message,
        "report_id": report.report_id
    }
