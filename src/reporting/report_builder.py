import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from ..decision_engine.trade_setup import TradeSetup
from ..analysis.data_models import Level, Pattern

class ReportBuilder:
    """Builds the final, comprehensive, user-specified report."""
    def __init__(self, config: dict):
        self.config = config

    def build_report(self, ranked_results: List[Dict[str, Any]], general_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        messages = []
        messages.append({"type": "header", "content": self._format_header(general_info)})
        for result in ranked_results:
            messages.append({"type": "timeframe", "content": self._format_timeframe_section(result)})

        final_message_content = self._format_combined_summary_and_trade(ranked_results)
        primary_rec = next((r for r in ranked_results if r.get('trade_setup')), None)
        messages.append({
            "type": "final_summary", "content": final_message_content,
            "keyboard": "follow_ignore" if primary_rec else None,
            "trade_setup": primary_rec.get('trade_setup') if primary_rec else None
        })
        return messages

    def _format_header(self, general_info: Dict) -> str:
        return (f"💎 تحليل فني شامل — {general_info.get('symbol', 'N/A')} 💎\n\n"
                f"المنصة: OKX Exchange\n"
                f"التاريخ والوقت: {datetime.now().strftime('%Y-%m-%d | %H:%M:%S')}\n"
                f"السعر الحالي: ${general_info.get('current_price', 0):,.2f}\n"
                f"نوع التحليل: {general_info.get('analysis_type', 'تحليل شامل')} ({' – '.join(general_info.get('timeframes', []))})")

    def _format_timeframe_section(self, result: Dict) -> str:
        timeframe, symbol, analysis = result.get('timeframe', 'N/A').upper(), result.get('symbol', 'N/A'), result.get('raw_analysis', {})
        patterns: List[Pattern] = analysis.get('patterns', [])
        p_status_map = {"Forming": "⏳ قيد التكوين", "Active": "✅ نشط / مفعل", "Failed": "❌ فشل"}
        section = f"🕐 فريم {timeframe} — {symbol}\n\n"
        if patterns:
            p = patterns[0]
            section += f"النموذج الفني: {p.name} — {p_status_map.get(p.status, p.status)}\n\n"
            section += f"شروط التفعيل:\n\nاختراق المقاومة ${p.activation_level:,.2f} مع ثبات شمعة {timeframe} فوقها.\n\n"
            section += f"شروط الإلغاء:\n\nكسر الدعم ${p.invalidation_level:,.2f} مع إغلاق شمعة {timeframe} تحته.\n\n"

        section += "🟢 الدعوم (أنواع وأسعار)\n\n" + self._format_levels(analysis.get('supports', []))
        section += "\n🔴 المقاومات (أنواع وأسعار)\n\n" + self._format_levels(analysis.get('resistances', []))

        fibo_levels = [lvl for lvl in analysis.get('supports', []) + analysis.get('resistances', []) if 'fibonacci' in lvl.name.lower()]
        if fibo_levels:
            section += f"\n📌 مستويات فيبوناتشي ({timeframe})\n\n"
            for lvl in sorted(fibo_levels, key=lambda x: x.value, reverse=True):
                if "0.5" in lvl.name: section += f"0.5 = ${lvl.value:,.2f}\n"
                if "0.618" in lvl.name: section += f"0.618 = ${lvl.value:,.2f}\n"
                if "0.786" in lvl.name: section += f"0.786 = ${lvl.value:,.2f}\n"
        return section

    def _format_levels(self, levels: List[Level]) -> str:
        level_texts = []
        level_map = {
            'دعم الاتجاه قصير المدى': ('دعم ترند قصير', '(ترند)'),
            'مقاومة الاتجاه قصير المدى': ('مقاومة ترند قصير', '(ترند)'),
            'دعم القناة السعرية': ('دعم قناة سعرية', '(قناة)'),
            'مقاومة القناة السعرية': ('مقاومة قناة سعرية', '(قناة)'),
            'fibonacci support': ('دعم فيبو', '(فايبو)'),
            'fibonacci resistance': ('مقاومة فيبو', '(فايبو)'),
            'fibonacci extension': ('مقاومة فيبو امتداد', '(فيبو امتداد)'),
            'دعم عام سابق': ('دعم عام سابق', '(سابق)'),
            'مقاومة عامة سابقة': ('مقاومة عامة سابقة', '(سابق)'),
            'volume profile poc': ('منطقة طلب عالية (POC)', '(POC)'),
            'high volume node': ('منطقة طلب عالية (HVN)', '(HVN)'),
        }

        for level in levels:
            if 'confluent' in level.name.lower():
                min_val, max_val = level.raw_data.get('range_min', level.value), level.raw_data.get('range_max', level.value)
                name_details = ""
                match = re.search(r'\((.*?)\)', level.name)
                if match: name_details = f" ({match.group(1)})"
                level_texts.append(f"منطقة مدمجة{name_details}: ${min_val:,.2f} – ${max_val:,.2f}")
                continue

            display_name, label = level.name, '(عام)'
            for key, (name, lbl) in level_map.items():
                if key in level.name.lower():
                    display_name, label = name, lbl
                    if "فيبو" in display_name:
                        ratio_match = re.search(r'(\d\.\d+)', level.name)
                        if ratio_match: display_name += f" {ratio_match.group(1)}"
                    break
            level_texts.append(f"{display_name}: ${level.value:,.2f} {label}")

        return "\n".join(level_texts) + "\n" if level_texts else "لا توجد مستويات واضحة.\n"

    def _format_combined_summary_and_trade(self, ranked_results: List[Dict]) -> str:
        summary_section = "📌 الملخص التنفيذي والصفقة المقترحة (مجمّع)\nالملخص لكل فريم مع حالة النجاح / الفشل\n\n"
        p_status_map = {"Forming": "⏳ قيد التكوين", "Active": "✅ مفعل / نشط", "Failed": "❌ فشل"}
        for res in ranked_results:
            p = res.get('raw_analysis', {}).get('patterns', [None])[0]
            if p:
                targets = ' → '.join([f"${t:,.0f}" for t in [p.target1, p.target2, p.target3] if t])
                summary_section += f"{res.get('timeframe').upper()}: {p.name} ({p_status_map.get(p.status, p.status)})\n"
                summary_section += f"نجاح النموذج: اختراق ${p.activation_level:,.0f} → أهداف: {targets}\n"
                summary_section += f"فشل النموذج: كسر ${p.invalidation_level:,.0f}\n\n"

        summary_section += "نقاط المراقبة الحرجة (مجمّعة)\n\nاختراقات المقاومة:\n"
        for res in ranked_results: summary_section += f"{res.get('timeframe').upper()} = ${res.get('raw_analysis', {}).get('patterns', [Pattern(name='', status='', timeframe='', activation_level=0, invalidation_level=0, target1=0)])[0].activation_level:,.0f}$\n"
        summary_section += "\nكسور الدعم:\n"
        for res in ranked_results: summary_section += f"{res.get('timeframe').upper()} = ${res.get('raw_analysis', {}).get('patterns', [Pattern(name='', status='', timeframe='', activation_level=0, invalidation_level=0, target1=0)])[0].invalidation_level:,.0f}$\n"

        primary_rec = next((r for r in ranked_results if r.get('trade_setup')), None)
        if not primary_rec or not primary_rec.get('trade_setup'): return summary_section

        setup: TradeSetup = primary_rec.get('trade_setup')
        summary_section += f"\n✅ الصفقة المؤكدة (مقترحة بعد دمج الفريمات)\n\nسعر الدخول المبدئي: {''.join(setup.confirmation_conditions)}.\n"
        if setup.optional_confirmation_conditions:
            summary_section += "\nشروط التأكيد الإضافية (اختياري لكن موصى به):\n\n" + "\n".join(f"- {cond}" for cond in setup.optional_confirmation_conditions) + "\n"

        summary_section += f"\nوقف الخسارة: كسر ${setup.stop_loss:,.2f} وإغلاق ساعة تحته (فريم {setup.timeframe.upper()}).\n"
        targets = [t for t in [setup.target1, setup.target2] if t]
        if targets:
            summary_section += f"\nالأهداف:\nهدف أول: ${targets[0]:,.2f}\n"
            if len(targets) > 1: summary_section += f"هدف ثاني: ${targets[1]:,.2f}\n"
            summary_section += f"تمدد محتمل: ${targets[-1] * 1.03:,.2f}\n"

        summary_section += "\nاستراتيجية دعم الفريمات:\n\n- إذا 4H يخترق المقاومة ويغلق 4 ساعات فوقها، فهذه إشارة كلاسيكية للنظر في زيادة المراكز (scaling in).\n- إذا 1D يخترق مقاومته الرئيسية، فهذا قد يحول الصفقة إلى استثمار طويل الأمد بأهداف عليا.\n- إذا أي فريم يكسر دعمه المعلن، فهذا حدث حرج يتطلب إعادة تقييم فورية للصفقة أو الخروج حسب سياسة إدارة المخاطر.\n"
        return summary_section
