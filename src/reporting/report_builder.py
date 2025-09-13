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
        """Constructs a list of messages to be sent."""
        messages = []

        # Message 1: Header
        messages.append({"type": "header", "content": self._format_main_header(general_info)})

        # Timeframe messages
        timeframe_emojis = {'1D': '📅', '4H': '🕓', '1H': '🕐', '30M': '🕒', '15M': '🕒', '5M': '🕔', '3M': '🕔'}
        sorted_results = sorted(ranked_results, key=lambda x: (
            {'1D': 0, '4H': 1, '1H': 2, '30M': 3, '15M': 4, '5M': 5, '3M': 6}.get(x.get('timeframe', '').upper(), 99)
        ))

        for result in sorted_results:
            timeframe = result.get('timeframe', 'N/A').upper()
            emoji = timeframe_emojis.get(timeframe, '⚙️')
            messages.append({
                "type": "timeframe",
                "content": self._format_timeframe_section(result, emoji)
            })

        # Summary message
        summary_content, primary_trade_setup = self._format_summary_section(sorted_results)
        messages.append({
            "type": "final_summary",
            "content": summary_content,
            "keyboard": "follow_ignore" if primary_trade_setup else None,
            "trade_setup": primary_trade_setup
        })

        return messages

    def _format_main_header(self, general_info: Dict) -> str:
        """Formats the main header based on the latest user template."""
        symbol = general_info.get('symbol', 'N/A').replace('-', '/')
        current_price = general_info.get('current_price', 0)
        analysis_type = general_info.get('analysis_type', 'تحليل شامل')
        timeframes = general_info.get('timeframes', [])

        return (
            f"💎 تحليل فني شامل - {symbol} 💎\n\n"
            f"المنصة: OKX Exchange\n"
            f"التاريخ والوقت: {datetime.now().strftime('%Y-%m-%d | %H:%M:%S')}\n"
            f"السعر الحالي: ${current_price:,.0f}\n"
            f"نوع التحليل: {analysis_type} ({' – '.join(timeframes)})"
        )

    def _format_timeframe_section(self, result: Dict, emoji: str) -> str:
        """Formats a single timeframe section based on the latest user template."""
        timeframe = result.get('timeframe', 'N/A').upper()
        symbol = result.get('symbol', 'N/A').replace('-', '/')
        analysis = result.get('raw_analysis', {})
        pattern: Optional[Pattern] = (analysis.get('patterns') or [None])[0]

        p_status_map = {"Forming": "قيد التكوين", "Active": "مفعل", "Failed": "فشل", "Completed": "مكتمل"}
        timeframe_full_name_map = {'1H': 'ساعة', '4H': '4 ساعات', '1D': 'يومية'}
        timeframe_name = timeframe_full_name_map.get(timeframe, timeframe)


        section = f"{emoji} فريم {timeframe} — {symbol}\n\n"

        if pattern and pattern.name:
            status_text = p_status_map.get(pattern.status, pattern.status)
            section += f"النموذج الفني: {pattern.name} ({status_text})\n"
            section += f"شروط التفعيل: اختراق المقاومة ${getattr(pattern, 'activation_level', 0):,.0f} مع ثبات شمعة {timeframe_name} فوقها\n"
            section += f"شروط الإلغاء: كسر الدعم ${getattr(pattern, 'invalidation_level', 0):,.0f} مع إغلاق شمعة {timeframe_name} تحته\n\n"

        supports = analysis.get('supports', [])
        resistances = analysis.get('resistances', [])

        if supports:
            section += "🟢 الدعوم\n" + self._format_levels(supports, is_support=True) + "\n"
        if resistances:
            section += "🔴 المقاومات\n" + self._format_levels(resistances, is_support=False)

        return section

    def _format_levels(self, levels: List[Level], is_support: bool) -> str:
        """Robustly formats levels based on the user's specific template."""
        level_texts = []
        for level in levels:
            name_lower = level.name.lower()
            display_name = level.name  # Default
            quality_label = f"({level.quality})" if level.quality else ""

            # Determine display name based on type
            if 'trend' in name_lower:
                display_name = f"دعم ترند {'قصير' if 'short' in name_lower else 'متوسط' if 'medium' in name_lower else 'طويل'}" if is_support else "مقاومة ترند"
            elif 'channel' in name_lower:
                display_name = "دعم قناة سعرية" if is_support else "مقاومة قناة سعرية"
            elif 'fibonacci' in name_lower:
                display_name = re.sub(r'resistance|support', '', level.name, flags=re.IGNORECASE).strip()
            elif 'high volume node' in name_lower or 'hvn' in name_lower:
                display_name = "منطقة طلب عالية" if is_support else "منطقة عرض عالية"
            elif 'previous' in name_lower or 'historical' in name_lower or 'عام' in name_lower:
                display_name = "دعم عام سابق" if is_support else "منطقة عرض عالية"
            elif 'poc' in name_lower:
                display_name = "مقاومة رئيسية"
            elif 'target' in name_lower:
                display_name = "مقاومة هدف النموذج"
            elif 'neckline' in name_lower:
                display_name = "خط عنق القاع المزدوج" if is_support else "خط عنق الرأس والكتفين"

            # Determine quality label based on user template
            if 'critical' in (level.quality or '').lower() or 'حرج' in (level.quality or ''):
                quality_label = "(حرج)"
            elif 'strong' in (level.quality or '').lower() or 'قوي' in (level.quality or ''):
                quality_label = "(قوي)"
            elif 'medium' in (level.quality or '').lower() or 'متوسط' in (level.quality or ''):
                quality_label = "(متوسط)"
            elif 'secondary' in (level.quality or '').lower() or 'ثانوي' in (level.quality or ''):
                quality_label = "(ثانوي)"
            elif 'bottom' in (level.quality or '').lower() or 'قاع' in (level.quality or ''):
                quality_label = "(قاع)"
            elif 'technical' in (level.quality or '').lower() or 'فني' in (level.quality or '') or 'target' in name_lower:
                quality_label = "(فني)"
            elif 'historical' in (level.quality or '').lower() or 'تاريخي' in (level.quality or ''):
                 quality_label = "(تاريخي)"


            level_texts.append(f"{display_name}: ${level.value:,.0f} {quality_label}")

        return "\n".join(level_texts) + "\n"

    def _format_summary_section(self, ranked_results: List[Dict]) -> (str, Optional[TradeSetup]):
        """Formats the final summary section dynamically and correctly."""
        summary = "📌 الملخص التنفيذي والشامل\n\n"

        p_status_map = {"Forming": "قيد التكوين", "Active": "مفعل", "Failed": "فشل"}
        timeframe_map = {'1H': 'قصير المدى', '4H': 'متوسط المدى', '1D': 'طويل المدى'}

        for res in ranked_results:
            tf = res.get('timeframe', 'N/A').upper()
            tf_name = timeframe_map.get(tf, tf)
            p: Optional[Pattern] = res.get('raw_analysis', {}).get('patterns', [None])[0]
            if p and p.name:
                status = p_status_map.get(p.status, p.status)
                targets = [t for t in [getattr(p, 'target1', None), getattr(p, 'target2', None), getattr(p, 'target3', None)] if t]
                targets_str = ' → '.join([f"${t:,.0f}" for t in targets])
                activation_str = f"${getattr(p, 'activation_level', 0):,.0f}"
                summary += f"{tf_name} ({tf}): {p.name} → اختراق {activation_str} → أهداف: {targets_str} → حالة النموذج: {status}\n"

        summary += "\nنقاط المراقبة الحرجة:\n"
        res_resistances, res_supports = [], []
        for r in ranked_results:
            pattern = r.get('raw_analysis', {}).get('patterns', [None])[0]
            if pattern and getattr(pattern, 'activation_level', 0):
                 res_resistances.append(f"{r.get('timeframe').upper()} = ${pattern.activation_level:,.0f}")
            if pattern and getattr(pattern, 'invalidation_level', 0):
                 res_supports.append(f"{r.get('timeframe').upper()} = ${pattern.invalidation_level:,.0f}")

        summary += f"اختراق المقاومة: {', '.join(res_resistances)}\n"
        summary += f"كسر الدعم: {', '.join(res_supports)}\n\n"

        primary_rec = next((r for r in ranked_results if r.get('trade_setup')), None)
        if not primary_rec or not primary_rec.get('trade_setup'):
            return summary, None

        setup: TradeSetup = primary_rec.get('trade_setup')

        summary += "صفقة مؤكدة:\n\n"
        entry_price_str = f"${setup.entry_price:,.0f}"
        stop_loss_str = f"${setup.stop_loss:,.0f}"
        targets = [t for t in [setup.target1, setup.target2] if t]
        targets_str = ' → '.join([f"${t:,.0f}" for t in targets])

        summary += f"سعر الدخول: عند اختراق {entry_price_str} (فريم {setup.timeframe.upper()}) مع ثبات 3 شموع ساعة فوقه\n"
        summary += f"الأهداف: {targets_str}\n"
        summary += f"وقف الخسارة: عند كسر {stop_loss_str}\n"

        # Dynamic Strategy Section
        strategy_text = self._generate_dynamic_strategy(setup, ranked_results)
        if strategy_text:
            summary += f"استراتيجية دعم الفريمات: {strategy_text}\n"

        return summary, setup

    def _generate_dynamic_strategy(self, primary_setup: TradeSetup, all_results: List[Dict]) -> str:
        """Generates a dynamic strategy text based on other timeframes as per user spec."""
        primary_tf = primary_setup.timeframe
        other_timeframes = [r for r in all_results if r.get('timeframe') != primary_tf and r.get('raw_analysis', {}).get('patterns', [None])[0]]

        if not other_timeframes:
            return ""

        timeframe_map = {'1H': 'للأهداف القصيرة', '4H': 'للأهداف المتوسطة', '1D': 'للأهداف الطويلة'}

        dynamic_parts = []
        for res in other_timeframes:
            tf = res.get('timeframe').upper()
            p: Optional[Pattern] = res.get('raw_analysis', {}).get('patterns', [None])[0]

            if p and getattr(p, 'activation_level', 0):
                activation_str = f"${p.activation_level:,.0f}"
                tf_target_desc = timeframe_map.get(tf, f"للأهداف على فريم {tf}")

                targets = [t for t in [getattr(p, 'target1', None), getattr(p, 'target2', None)] if t]
                if len(targets) > 1:
                    targets_str = f"{tf_target_desc} ${targets[0]:,.0f} – ${targets[1]:,.0f}"
                elif len(targets) == 1:
                    targets_str = f"{tf_target_desc} ${targets[0]:,.0f}"
                else:
                    targets_str = ""

                if targets_str:
                    dynamic_parts.append(f"متابعة {tf} لاختراق {activation_str} {targets_str}")

        return "، ".join(dynamic_parts)
