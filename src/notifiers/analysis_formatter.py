from typing import List, Dict, Any
import uuid

# Use a try-except block for robust importing
try:
    from src.analysis.models import AnalysisReport, TimeframeAnalysis
except ImportError:
    # This allows the file to be potentially used in different contexts
    from analysis.models import AnalysisReport, TimeframeAnalysis


def format_timeframe_message(timeframe_analysis: TimeframeAnalysis, pair: str) -> str:
    """Formats a single timeframe analysis into a string message, using HTML for style."""
    supports_str = "\n".join([f"- {s.type}: <b>{s.level}$</b> ({s.strength})" for s in timeframe_analysis.supports])
    resistances_str = "\n".join([f"- {r.type}: <b>{r.level}$</b> ({r.strength})" for r in timeframe_analysis.resistances])

    message = f"""
<b>🕐 فريم {timeframe_analysis.timeframe} — {pair}</b>
السعر الحالي: <b>{timeframe_analysis.current_price}$</b>

<b>📊 النموذج الفني: {timeframe_analysis.pattern.name} ({timeframe_analysis.pattern.status})</b>
<i>شروط التفعيل:</i> {timeframe_analysis.pattern.activation_condition}
<i>شروط الإلغاء:</i> {timeframe_analysis.pattern.invalidation_condition}

<b>🟢 الدعوم</b>
{supports_str}

<b>🔴 المقاومات</b>
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
<b>📌 الملخص التنفيذي والشامل</b>
<b>قصير المدى:</b> {summary.short_term_summary}
<b>متوسط المدى:</b> {summary.medium_term_summary}
<b>طويل المدى:</b> {summary.long_term_summary}

<b>نقاط المراقبة الحرجة:</b>
{summary.critical_points.get('resistance_breakout', 'N/A')}
{summary.critical_points.get('support_breakdown', 'N/A')}
"""

    trade_str = f"""
<b>📌 صفقة مؤكدة بعد دمج الفريمات الثلاثة</b>
<b>سعر الدخول المبدئي:</b> {trade.entry_price_condition}
<b>الأهداف:</b> {' → '.join(map(str, trade.targets))}$
<b>وقف الخسارة:</b> {trade.stop_loss_condition}
<b>استراتيجية دعم الفريمات:</b>
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
💎 <b>تحليل فني شامل - {report.pair}</b> 💎

<b>المنصة:</b> {report.platform}
<b>التاريخ والوقت:</b> {report.timestamp.strftime('%Y-%m-%d | %H:%M:%S')}
<b>السعر الحالي:</b> {report.timeframe_analyses[0].current_price}$
<b>نوع التحليل:</b> {report.analysis_type}
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
