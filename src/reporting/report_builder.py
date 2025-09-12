import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from ..decision_engine.trade_setup import TradeSetup
from ..analysis.data_models import Level, Pattern

class ReportBuilder:
    """
    Builds a human-readable, multi-part report from analysis results,
    formatted according to the new user-specified template.
    """
    def __init__(self, config: dict):
        self.config = config

    def build_report(self, ranked_results: List[Dict[str, Any]], general_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Builds the full report as a list of message dictionaries.
        """
        messages = []

        # 1. Header Message
        header_content = self._format_header(general_info)
        messages.append({"type": "header", "content": header_content, "keyboard": None})

        # 2. Individual Timeframe Messages
        for result in ranked_results:
            timeframe_content = self._format_timeframe_section(result)
            messages.append({"type": "timeframe", "content": timeframe_content, "keyboard": None})

        # 3. Final Combined Summary & Trade Setup Message
        final_message_content = self._format_combined_summary_and_trade(ranked_results)

        primary_rec = next((r for r in ranked_results if r.get('trade_setup')), None)
        keyboard_type = "follow_ignore" if primary_rec else None

        messages.append({
            "type": "final_summary",
            "content": final_message_content,
            "keyboard": keyboard_type,
            "trade_setup": primary_rec.get('trade_setup') if primary_rec else None
        })

        for msg in messages:
            msg['ranked_results'] = ranked_results

        return messages

    def _format_header(self, general_info: Dict) -> str:
        symbol = general_info.get('symbol', 'N/A')
        current_price = general_info.get('current_price', 0)
        analysis_type = general_info.get('analysis_type', 'تحليل شامل')
        timeframes = general_info.get('timeframes', [])
        timeframe_str = " – ".join(tf.upper() for tf in timeframes) if timeframes else ""

        return (f"💎 تحليل فني شامل - {symbol} 💎\n\n"
                f"المنصة: OKX Exchange\n"
                f"التاريخ والوقت: {datetime.now().strftime('%Y-%m-%d | %H:%M:%S')}\n"
                f"السعر الحالي: ${current_price:,.2f}\n"
                f"نوع التحليل: {analysis_type} ({timeframe_str})")

    def _format_timeframe_section(self, result: Dict) -> str:
        timeframe = result.get('timeframe', 'N/A').upper()
        symbol = result.get('symbol', 'N/A')
        current_price = result.get('current_price', 0)
        analysis = result.get('raw_analysis', {})
        patterns: List[Pattern] = analysis.get('patterns', [])

        section = f"🕐 فريم {timeframe} — {symbol}\n"
        section += f"السعر الحالي: ${current_price:,.2f}\n\n"

        if patterns:
            p = patterns[0]
            section += f"📊 النموذج الفني: {p.name} — {p.status}\n\n"
            activation_text = f"اختراق المقاومة ${p.activation_level:,.2f} مع ثبات شمعة {timeframe} فوقها"
            invalidation_text = f"كسر الدعم ${p.invalidation_level:,.2f} مع إغلاق شمعة {timeframe} تحته"
            section += f"شروط التفعيل: {activation_text}\n"
            section += f"شروط الإلغاء: {invalidation_text}\n\n"
        else:
            section += "📊 النموذج الفني: لا يوجد نموذج واضح حاليًا.\n\n"

        supports: List[Level] = analysis.get('supports', [])
        resistances: List[Level] = analysis.get('resistances', [])

        section += "🟢 الدعوم\n"
        section += self._format_levels(supports, 'support', patterns)

        section += "\n🔴 المقاومات\n"
        section += self._format_levels(resistances, 'resistance', patterns)

        return section

    def _format_levels(self, levels: List[Level], level_type: str, patterns: List[Pattern]) -> str:
        level_texts = []

        level_map = {
            'trend': 'دعم ترند',
            'channel': 'دعم قناة سعرية',
            'fibonacci support 0.618': 'دعم فيبو 0.618',
            'fibonacci support 0.5': 'دعم فيبو 0.5',
            'دعم عام سابق': 'دعم عام سابق', # Exact match for the new level type
            'confluent': 'دعم منطقة مدمجة',
        }
        if level_type == 'resistance':
            level_map = {
                'trend': 'مقاومة ترند',
                'channel': 'مقاومة قناة سعرية',
                'fibonacci resistance': 'مقاومة فيبو',
                'fibonacci extension': 'مقاومة فيبو امتداد',
                'مقاومة عامة سابقة': 'مقاومة عامة سابقة', # Exact match
                'confluent': 'مقاومة منطقة مدمجة',
            }

        formatted_levels = set()
        for level in levels:
            key_found = False
            for key, text in level_map.items():
                if key in level.name.lower():
                    # Special handling for confluent zones to show what they contain
                    if 'confluent' in key:
                        text = f"{text} ({level.name.split('(')[-1]}"
                    level_texts.append(f"{text}: ${level.value:,.2f} ({level.quality})")
                    formatted_levels.add(key)
                    key_found = True
                    break
            if not key_found:
                 level_texts.append(f"{level.name}: ${level.value:,.2f} ({level.quality})")

        if patterns:
            p = patterns[0]
            if level_type == 'resistance' and 'target' not in formatted_levels:
                level_texts.append(f"مقاومة هدف النموذج: ${p.target1:,.2f} (فني)")
            if level_type == 'resistance' and p.target2:
                level_texts.append(f"مقاومة هدف النموذج 2: ${p.target2:,.2f} (فني)")

        # The new approach is to only show what is found, so no placeholders.
        # The 'unsupported_analysis_fields.txt' file serves as documentation for what is out of scope.
        # if level_type == 'support':
        #     level_texts.append("منطقة طلب عالية: (غير مدعوم حاليًا)")
        # else:
        #     level_texts.append("منطقة عرض عالية: (غير مدعوم حاليًا)")

        if not level_texts:
            return "لا توجد مستويات واضحة.\n"

        return "\n".join(level_texts) + "\n"

    def _format_combined_summary_and_trade(self, ranked_results: List[Dict]) -> str:
        if not ranked_results:
            return "📌 الملخص التنفيذي والشامل\n\nلا تتوفر بيانات كافية."

        summary_section = "📌 الملخص التنفيذي والشامل\n\n"
        timeframe_groups = self.config.get('trading', {}).get('TIMEFRAME_GROUPS', {})
        horizon_map = {tf: horizon for horizon, tfs in timeframe_groups.items() for tf in tfs}
        horizon_names = {'short_term': 'قصير المدى', 'medium_term': 'متوسط المدى', 'long_term': 'طويل المدى'}

        for res in ranked_results:
            p = res.get('raw_analysis', {}).get('patterns', [None])[0]
            if p:
                horizon_key = horizon_map.get(res.get('timeframe', '').upper(), 'N/A')
                horizon_name = horizon_names.get(horizon_key, 'غير محدد')
                targets = [t for t in [p.target1, p.target2, p.target3] if t]
                target_str = ' → '.join([f"${t:,.0f}" for t in targets])
                summary_section += f"{horizon_name} ({res.get('timeframe').upper()}): {p.name} → اختراق {p.activation_level:,.0f}$ → أهداف: {target_str}\n"

        summary_section += "\nنقاط المراقبة الحرجة:\n"
        activations = [f"{res.get('timeframe').upper()} = ${res.get('raw_analysis', {}).get('patterns', [Pattern(name='', status='', timeframe='', activation_level=0, invalidation_level=0, target1=0)])[0].activation_level:,.0f}" for res in ranked_results if res.get('raw_analysis', {}).get('patterns')]
        invalidations = [f"{res.get('timeframe').upper()} = ${res.get('raw_analysis', {}).get('patterns', [Pattern(name='', status='', timeframe='', activation_level=0, invalidation_level=0, target1=0)])[0].invalidation_level:,.0f}" for res in ranked_results if res.get('raw_analysis', {}).get('patterns')]
        summary_section += f"اختراق المقاومة: {', '.join(activations)}\n"
        summary_section += f"كسر الدعم: {', '.join(invalidations)}\n"

        primary_rec = next((r for r in ranked_results if r.get('trade_setup')), None)

        trade_section = "\n📌 صفقة مؤكدة بعد دمج الفريمات الثلاثة\n\n"
        if not primary_rec or not primary_rec.get('trade_setup'):
            trade_section += "لا توجد صفقة مؤكدة بشروط واضحة في الوقت الحالي."
            return summary_section + trade_section

        setup: TradeSetup = primary_rec.get('trade_setup')

        entry_conditions = f"عند اختراق ${setup.entry_price:,.2f} (فريم {setup.timeframe.upper()})"
        if setup.confirmation_conditions:
            entry_conditions += f" مع {setup.confirmation_conditions[0]}"
        trade_section += f"سعر الدخول المبدئي: {entry_conditions}\n"

        targets = [t for t in [setup.target1, setup.target2] if t]
        target_str = ' → '.join([f"${t:,.2f}" for t in targets])
        if targets:
            potential_ext = targets[-1] * 1.03
            target_str += f" → تمدد محتمل ${potential_ext:,.2f}"
        trade_section += f"الأهداف: {target_str}\n"

        trade_section += f"وقف الخسارة: عند كسر ${setup.stop_loss:,.2f} (فريم {setup.timeframe.upper()})\n\n"

        trade_section += "استراتيجية دعم الفريمات:\n"
        supporting_recs = [r for r in ranked_results if r.get('trade_setup') and r['trade_setup'] != setup]
        if supporting_recs:
            for res in supporting_recs:
                other_setup = res['trade_setup']
                other_targets = [t for t in [other_setup.target1, other_setup.target2] if t]
                other_target_str = ' – '.join([f"${t:,.2f}" for t in other_targets])
                trade_section += f"متابعة فريم {other_setup.timeframe.upper()} لاختراق ${other_setup.entry_price:,.2f} → أهداف {other_target_str}\n"
        else:
            trade_section += "لا توجد أطر زمنية داعمة أخرى للمراقبة.\n"

        return summary_section + trade_section
