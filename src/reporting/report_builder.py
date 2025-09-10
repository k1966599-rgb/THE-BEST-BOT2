from typing import List, Dict, Any
from datetime import datetime
from ..decision_engine.trade_setup import TradeSetup
from ..analysis.data_models import Level, Pattern

class ReportBuilder:
    def __init__(self, config: dict):
        self.config = config

    def build_report(self, ranked_results: List[Dict[str, Any]], general_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Builds the full report by assembling its components.
        """
        header = self._format_header(general_info)

        timeframe_reports = []
        for i, result in enumerate(ranked_results):
            timeframe_reports.append(self._format_timeframe_section(result, i + 1))

        summary = self._format_summary(ranked_results)
        final_recommendation = self._format_final_recommendation(ranked_results)

        return {
            "header": header,
            "timeframe_reports": timeframe_reports,
            "summary": summary,
            "final_recommendation": final_recommendation,
            "ranked_results": ranked_results
        }

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

    def _format_timeframe_section(self, result: Dict, priority: int) -> str:
        """
        Formats a single timeframe's analysis into a string.
        """
        timeframe = result.get('timeframe', 'N/A').upper()
        symbol = result.get('symbol', 'N/A')
        current_price = result.get('current_price', 0)
        analysis = result.get('raw_analysis', {})

        supports: List[Level] = analysis.get('supports', [])
        resistances: List[Level] = analysis.get('resistances', [])
        patterns: List[Pattern] = analysis.get('patterns', [])

        section = f"🕐 فريم {timeframe} — {symbol}\n"
        section += f"السعر الحالي: ${current_price:,.2f}\n\n"

        if patterns:
            p = patterns[0]
            section += f"📊 النموذج الفني: {p.name} — {p.status}\n\n"
            section += f"شروط التفعيل: اختراق المقاومة ${p.activation_level:,.2f} مع ثبات شمعة {timeframe} فوقها\n\n"
            section += f"شروط الإلغاء: كسر الدعم ${p.invalidation_level:,.2f} مع إغلاق شمعة {timeframe} تحته\n\n"
        else:
            section += "📊 النموذج الفني: لا يوجد نموذج واضح حاليًا.\n\n"

        section += "🟢 الدعوم\n\n"
        if supports:
            for s in supports:
                section += f"{s.name}: ${s.value:,.2f} ({s.quality})\n\n"
        else:
            section += "لا توجد دعوم واضحة.\n\n"

        section += "🔴 المقاومات\n\n"
        if resistances:
            for r in resistances:
                section += f"{r.name}: ${r.value:,.2f} ({r.quality})\n\n"
        else:
            section += "لا توجد مقاومات واضحة.\n\n"

        return section

    def _format_summary(self, ranked_results: List[Dict]) -> str:
        if not ranked_results:
            return "📌 الملخص التنفيذي والشامل\n\nلا توجد بيانات كافية."

        summary = "📌 الملخص التنفيذي والشامل\n\n"
        timeframe_groups = self.config.get('trading', {}).get('TIMEFRAME_GROUPS', {})
        horizon_map = {tf: horizon for horizon, tfs in timeframe_groups.items() for tf in tfs}

        grouped_results = {'long': [], 'medium': [], 'short': []}
        for res in ranked_results:
            horizon = horizon_map.get(res.get('timeframe'))
            if horizon:
                grouped_results[horizon].append(res)

        for horizon, name in [('long', 'طويل المدى'), ('medium', 'متوسط المدى'), ('short', 'قصير المدى')]:
            results_in_horizon = grouped_results.get(horizon, [])
            if not results_in_horizon: continue

            best_res = results_in_horizon[0]
            patterns: List[Pattern] = best_res.get('raw_analysis', {}).get('patterns', [])

            if patterns:
                p = patterns[0]
                targets = [t for t in [p.target1, p.target2, p.target3] if t]
                target_str = ' → '.join([f"${t:,.0f}" for t in targets])
                summary += f"{name} ({best_res.get('timeframe').upper()}): {p.name} → اختراق ${p.activation_level:,.0f} → أهداف: {target_str}\n\n"

        summary += "📌 نقاط المراقبة الحرجة:\n"
        breakout_points = [f"{res.get('timeframe').upper()} = ${res.get('raw_analysis', {}).get('patterns', [Pattern(name='', status='', timeframe='', activation_level=0, invalidation_level=0, target1=0)])[0].activation_level:,.0f}" for res in ranked_results if res.get('raw_analysis', {}).get('patterns')]
        summary += "اختراق المقاومة: " + ', '.join(breakout_points) + "\n"

        breakdown_points = [f"{res.get('timeframe').upper()} = ${res.get('raw_analysis', {}).get('patterns', [Pattern(name='', status='', timeframe='', activation_level=0, invalidation_level=0, target1=0)])[0].invalidation_level:,.0f}" for res in ranked_results if res.get('raw_analysis', {}).get('patterns')]
        summary += "كسر الدعم: " + ', '.join(breakdown_points) + "\n"

        return summary

    def _format_final_recommendation(self, ranked_results: List[Dict]) -> str:
        primary_rec = next((r for r in ranked_results if r.get('trade_setup')), None)
        if not primary_rec or not primary_rec.get('trade_setup'):
            return "📌 صفقة مؤكدة\n\n❌ لا توجد توصية واضحة بمواصفات كاملة حاليًا."

        setup: TradeSetup = primary_rec.get('trade_setup')
        rec_text = "📌 صفقة مؤكدة بعد دمج الفريمات الثلاثة\n\n"

        # Format confirmation conditions
        conditions_str = "\n".join([f"- {cond}" for cond in setup.confirmation_conditions])
        rec_text += f"شروط الدخول المبدئي:\n{conditions_str}\n\n"

        targets = [t for t in [setup.target1, setup.target2] if t]
        target_str = ' → '.join([f"${t:,.2f}" for t in targets])
        potential_target = (targets[-1] * 1.05) if targets else (setup.entry_price * 1.05)
        target_str += f" → تمدد محتمل ${potential_target:,.2f}"
        rec_text += f"الأهداف: {target_str}\n\n"

        rec_text += f"وقف الخسارة: عند كسر ${setup.stop_loss:,.2f} (فريم {setup.timeframe.upper()})\n\n"

        rec_text += "استراتيجية دعم الفريمات:\n"
        supporting_recs = [r for r in ranked_results if r.get('trade_setup') and r['trade_setup'] != setup]
        if supporting_recs:
            for res in supporting_recs:
                other_setup = res['trade_setup']
                other_targets = [t for t in [other_setup.target1, other_setup.target2] if t]
                other_target_str = ' – '.join([f"${t:,.2f}" for t in other_targets])
                rec_text += f"متابعة فريم {other_setup.timeframe.upper()} لاختراق ${other_setup.entry_price:,.2f} → أهداف {other_target_str}\n"
        else:
            rec_text += "لا توجد فريمات أخرى داعمة حاليًا.\n"

        return rec_text
