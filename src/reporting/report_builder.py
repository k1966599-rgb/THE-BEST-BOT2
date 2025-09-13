import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from ..decision_engine.trade_setup import TradeSetup
from ..analysis.data_models import Level, Pattern

class ReportBuilder:
    """
    Builds the final, comprehensive, user-specified report in a multi-message format.
    """
    def __init__(self, config: dict):
        self.config = config

    def build_report(self, ranked_results: List[Dict[str, Any]], general_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Constructs a list of messages to be sent.

        1.  Header Message
        2.  Timeframe-specific analysis messages (one for each)
        3.  Final Summary & Trade Proposal
        """
        messages = []

        # Message 1: Basic Info Header
        messages.append({"type": "header", "content": self._format_message_1_header(general_info)})

        # Messages 2, 3, 4...: Timeframe Analyses
        sorted_results = sorted(ranked_results, key=lambda x: (
            {'1D': 0, '4H': 1, '1H': 2, '30m': 3, '15m': 4, '5m': 5, '3m': 6}.get(x.get('timeframe', '').upper(), 99)
        ))

        message_number = 2
        for result in sorted_results:
            messages.append({
                "type": "timeframe",
                "content": self._format_message_2_timeframe(result, message_number)
            })
            message_number += 1

        # Final Message: Summary and Trade Proposal
        final_message_content, primary_trade_setup = self._format_message_5_summary(sorted_results, message_number)
        messages.append({
            "type": "final_summary",
            "content": final_message_content,
            "keyboard": "follow_ignore" if primary_trade_setup else None,
            "trade_setup": primary_trade_setup
        })

        return messages

    def _format_message_1_header(self, general_info: Dict) -> str:
        """Formats Message 1: Basic Analysis Information."""
        symbol = general_info.get('symbol', 'N/A')
        current_price = general_info.get('current_price', 0)
        analysis_type = general_info.get('analysis_type', 'تحليل شامل')
        timeframes = general_info.get('timeframes', [])

        return (
            f"📩 الرسالة الأولى — معلومات التحليل الأساسية\n\n"
            f"اسم العملة: {symbol.replace('-', '/')}\n"
            f"المنصة: OKX Exchange\n"
            f"التاريخ والوقت: {datetime.now().strftime('%Y-%m-%d | %H:%M:%S')}\n"
            f"السعر الحالي: ${current_price:,.3f}\n"
            f"نوع التحليل: {analysis_type} ({' – '.join(timeframes)})"
        )

    def _format_message_2_timeframe(self, result: Dict, message_number: int) -> str:
        """Formats a message for a single timeframe analysis."""
        timeframe = result.get('timeframe', 'N/A').upper()
        analysis = result.get('raw_analysis', {})
        pattern: Optional[Pattern] = analysis.get('patterns', [None])[0]

        # Mapping for pattern status
        p_status_map = {"Forming": "⏳ قيد التكوين", "Active": "✅ مفعل / نشط", "Failed": "❌ فشل", "Completed": "✅ مكتمل"}

        # Message header
        section = f"📩 الرسالة {message_number} — فريم {timeframe}\n\n"

        # Technical Pattern
        if pattern and pattern.name:
            status_text = p_status_map.get(pattern.status, pattern.status)
            section += f"النموذج الفني: {pattern.name} — {status_text}\n\n"
            section += f"شروط تفعيل النموذج:\n"
            section += f"اختراق المقاومة ${getattr(pattern, 'activation_level', 0):,.3f} مع إغلاق شمعة {timeframe} فوقها.\n\n"
            section += f"شروط إلغاء/فشل النموذج:\n"
            section += f"كسر الدعم ${getattr(pattern, 'invalidation_level', 0):,.3f} مع إغلاق شمعة {timeframe} تحته.\n\n"
        else:
            section += "النموذج الفني: لا يوجد نموذج واضح حاليًا.\n\n"

        # Supports and Resistances
        section += "🟢 الدعوم (نوع السعر)\n" + self._format_levels(analysis.get('supports', []), is_support=True) + "\n"
        section += "🔴 المقاومات (نوع السعر)\n" + self._format_levels(analysis.get('resistances', []), is_support=False) + "\n"

        # Fibonacci Levels
        fibo_levels = {
            "0.5": None, "0.618": None, "0.786": None
        }
        all_levels = analysis.get('supports', []) + analysis.get('resistances', [])
        for lvl in all_levels:
            if 'fibonacci' in lvl.name.lower():
                if "0.5" in lvl.name: fibo_levels["0.5"] = lvl.value
                if "0.618" in lvl.name: fibo_levels["0.618"] = lvl.value
                if "0.786" in lvl.name: fibo_levels["0.786"] = lvl.value

        fibo_text = f"📌 مستويات فيبوناتشي المهمة ({timeframe})\n"
        has_fibo = False
        for ratio, value in fibo_levels.items():
            if value is not None:
                fibo_text += f"{ratio} = ${value:,.3f}\n"
                has_fibo = True

        if has_fibo:
            section += fibo_text

        return section

    def _format_levels(self, levels: List[Level], is_support: bool) -> str:
        """Helper to format support or resistance levels with specific user-requested names."""
        level_texts = []

        # Sort levels by value, descending for resistance, ascending for support
        levels.sort(key=lambda x: x.value, reverse=not is_support)

        for level in levels:
            name, label = "غير محدد", "(عام)"

            # More specific mapping based on user request
            name_lower = level.name.lower()

            # Check for keywords in both English and Arabic to handle inconsistent naming
            if 'trend' in name_lower or 'اتجاه' in name_lower:
                name, label = (f"دعم ترند {'متوسط' if 'medium' in name_lower else 'قصير'}", "(ترند)") if is_support else ("مقاومة ترند", "(ترند)")
            elif 'channel' in name_lower or 'قناة' in name_lower:
                name, label = ("دعم قناة سعرية", "(قناة)") if is_support else ("مقاومة قناة سعرية", "(قناة)")
            elif 'fibonacci' in name_lower:
                ratio_match = re.search(r'(\d\.\d+)', name_lower)
                ratio = f" {ratio_match.group(1)}" if ratio_match else ""
                name, label = (f"دعم فيبو{ratio}", "(فايبو)") if is_support else (f"مقاومة فيبو امتداد", "(فيبو امتداد)")
            elif 'previous' in name_lower or 'عام' in name_lower or 'تاريخي' in name_lower:
                name, label = ("دعم عام سابق", "(سابق)") if is_support else ("مقاومة عامة سابقة", "(سابق)")
            elif 'poc' in name_lower:
                name, label = ("منطقة طلب عالية (POC)", "(POC)") if is_support else ("مقاومة رئيسية", "(POC/مقاومة رئيسية)")
            elif 'hvn' in name_lower or 'high volume node' in name_lower:
                name, label = ("منطقة طلب عالية (HVN)", "(HVN)") if is_support else ("منطقة عرض عالية (HVN)", "(HVN)")
            elif 'confluent' in name_lower:
                min_val, max_val = level.raw_data.get('range_min', level.value), level.raw_data.get('range_max', level.value)
                label = "(Confluent)"
                name = "دعم منطقة مدمجة" if is_support else "مقاومة منطقة مدمجة"
                level_texts.append(f"{name}: ${min_val:,.3f} – ${max_val:,.3f} {label}")
                continue
            elif 'target' in name_lower: # Changed to elif to prevent relabeling
                name, label = "مقاومة هدف النموذج", "(هدف فني)"
            else: # If no specific category, use a generic name but still display it
                name, label = (f"دعم {level.name}", "(عام)") if is_support else (f"مقاومة {level.name}", "(عام)")


            level_texts.append(f"{name}: ${level.value:,.3f} {label}")

        return "\n".join(level_texts) + "\n" if level_texts else "لا توجد مستويات واضحة.\n"

    def _format_message_5_summary(self, ranked_results: List[Dict], message_number: int) -> (str, Optional[TradeSetup]):
        """Formats the final summary message and identifies the primary trade setup."""
        summary = f"📩 الرسالة {message_number} — الملخص التنفيذي والصفقة المقترحة (مجمّع)\n"
        summary += "الملخص لكل فريم مع حالة النجاح / الفشل\n\n"

        p_status_map = {"Forming": "⏳ قيد التكوين", "Active": "✅ مفعل / نشط", "Failed": "❌ فشل"}

        # Timeframe Summaries
        for res in ranked_results:
            tf = res.get('timeframe', 'N/A').upper()
            p: Optional[Pattern] = res.get('raw_analysis', {}).get('patterns', [None])[0]
            if p and p.name:
                status = p_status_map.get(p.status, p.status)
                summary += f"{tf}: {p.name} ({status})\n"

                # Add all three targets and use integer formatting for cleaner display
                all_targets = [t for t in [getattr(p, 'target1', None), getattr(p, 'target2', None), getattr(p, 'target3', None)] if t]
                targets_str = ' → '.join([f"${t:,.0f}" for t in all_targets])

                # Use integer formatting for activation/invalidation levels
                activation_level_str = f"${getattr(p, 'activation_level', 0):,.0f}"
                invalidation_level_str = f"${getattr(p, 'invalidation_level', 0):,.0f}"

                if targets_str:
                    summary += f"نجاح: اختراق {activation_level_str} → أهداف: {targets_str}\n"
                else:
                    summary += f"نجاح: اختراق {activation_level_str}\n"

                summary += f"فشل: كسر {invalidation_level_str}\n\n"

        # Critical Monitoring Points (safer implementation)
        summary += "نقاط المراقبة الحرجة (مجمّعة)\n"
        res_resistances, res_supports = [], []
        for r in ranked_results:
            pattern = r.get('raw_analysis', {}).get('patterns', [None])[0]
            if pattern:
                if getattr(pattern, 'activation_level', 0):
                    res_resistances.append(f"{r.get('timeframe').upper()} = ${pattern.activation_level:,.0f}")
                if getattr(pattern, 'invalidation_level', 0):
                    res_supports.append(f"{r.get('timeframe').upper()} = ${pattern.invalidation_level:,.0f}")

        summary += f"اختراقات المقاومة: {' | '.join(res_resistances)}\n"
        summary += f"كسور الدعم: {' | '.join(res_supports)}\n\n"

        # Find the primary trade recommendation
        primary_rec = next((r for r in ranked_results if r.get('trade_setup')), None)
        if not primary_rec or not primary_rec.get('trade_setup'):
            return summary, None

        setup: TradeSetup = primary_rec.get('trade_setup')

        # Proposed Trade Section
        summary += "✅ الصفقة المؤكدة (مقترحة بعد دمج الفريمات)\n\n"
        entry_condition_text = f"ثبات السعر فوق ${setup.entry_price:,.3f}"
        if setup.confirmation_rule:
            if '3_candle' in setup.confirmation_rule:
                entry_condition_text += f" مع إغلاق 3 شمعات {setup.timeframe} متتالية فوقه."
            else:
                entry_condition_text += " مع تأكيد الإغلاق."
        else:
            entry_condition_text += "."

        summary += f"سعر الدخول المبدئي: {entry_condition_text}\n\n"

        summary += "شروط التأكيد الإضافية (موصى بها):\n"
        summary += "- OBV متزايد أثناء/بعد الاختراق.\n"
        summary += "- MACD تقاطع صاعد أو ميل إيجابي.\n"
        summary += "- ADX > 20–25 لدعم قوة الاتجاه.\n"
        summary += "- ATR في تصاعد أو مرتفع لدعم قوة الحركة.\n\n"

        summary += f"وقف الخسارة: كسر ${setup.stop_loss:,.3f} مع إغلاق ساعة تحته (فريم {setup.timeframe.upper()}).\n\n"

        summary += "الأهداف:\n"
        if setup.target1: summary += f"هدف أول: ${setup.target1:,.3f}\n"
        if setup.target2: summary += f"هدف ثاني: ${setup.target2:,.3f}\n"
        if setup.target2: summary += f"تمدد محتمل: ${setup.target2 * 1.05:,.3f}\n\n" # Example of extension

        # Multi-timeframe Strategy
        summary += "استراتيجية دعم الفريمات أثناء الصفقة\n"
        if '4H' in [r['timeframe'] for r in ranked_results]:
            summary += "- إذا فريم 4H يخترق مقاومته ويغلق 4 ساعات فوقها → النظر في زيادة المركز تدريجيًا (scaling in).\n"
        if '1D' in [r['timeframe'] for r in ranked_results]:
            summary += "- إذا فريم 1D يخترق مقاومته ويغلق يومياً فوقه → تحويل جزء من المراكز لأهداف طويلة المدى.\n"
        summary += "- إذا أي فريم يكسر الدعم المعلن (إغلاق شمعة على الفريم المناسب أسفل الدعم) → إعادة تقييم فورية أو إغلاق حسب سياسة المخاطرة.\n"

        return summary, setup
