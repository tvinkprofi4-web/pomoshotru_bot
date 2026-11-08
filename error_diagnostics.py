# -*- coding: utf-8 -*-
"""
error_diagnostics.py — Глубокая диагностика и логирование ошибок бота.

1) BotExceptionHandler подключается к TeleBot и ловит ЛЮБЫЕ необработанные
   исключения в хендлерах: локализует файл:строку, пишет в журнал
   learning_experience (SQLite) и мгновенно шлёт Создателям алерт.
2) Новые (первичные) сигнатуры ошибок автоматически анализируются GLM-5.3
   через Verboo Router (self_evolution.call_glm_self_update): первопричина,
   локализация и готовый патч — отдельным сообщением Создателям.
3) Команда !логи / /логи (только Создатели): журнал последних ошибок,
   !логи анализ — GLM-разбор самой свежей/частой ошибки с патчем.
"""

import os
import time
import html
import logging
import threading
import traceback

import telebot

import config
import database

logger = logging.getLogger(__name__)

# Создатели — получают алерты и имеют доступ к журналу (иммунитет неприкосновенен)
CREATOR_ALERT_IDS = [6363403785, 7758799391]

PE = {
    "alert": '<tg-emoji emoji-id="5204004249549154638">🚨</tg-emoji>',
    "pin": '<tg-emoji emoji-id="5469882585100339882">📍</tg-emoji>',
    "bug": '<tg-emoji emoji-id="5454064486837133402">🐞</tg-emoji>',
    "repeat": '<tg-emoji emoji-id="5429633836684157942">🔁</tg-emoji>',
    "clock": '<tg-emoji emoji-id="5449623537897721918">🕒</tg-emoji>',
    "wrench": '<tg-emoji emoji-id="5255797273056544167">🔧</tg-emoji>',
    "brain": '<tg-emoji emoji-id="5377510010500699911">🧠</tg-emoji>',
    "check": '<tg-emoji emoji-id="5413721644277441416">✅</tg-emoji>',
    "cross": '<tg-emoji emoji-id="5429452773747860261">❌</tg-emoji>',
    "bulb": '<tg-emoji emoji-id="5370933273109221746">💡</tg-emoji>',
    "stethoscope": '<tg-emoji emoji-id="5370933273109221746">🩺</tg-emoji>',
}

# Окно подавления дублей алертов по одной сигнатуре (сек)
ALERT_DEDUPE_WINDOW = 900
# Минимальный интервал между авто-запросами GLM-анализа (сек)
GLM_AUTO_ANALYSIS_COOLDOWN = 600

_bot_instance = None
_last_alert_ts = {}
_last_glm_ts = {"ts": 0.0}
_alert_lock = threading.Lock()

PROJECT_FILES = ("bot.py", "database.py", "moderation.py", "self_evolution.py",
                 "web_app.py", "custom_features.py", "db_sync.py", "error_diagnostics.py",
                 "youtube_helper.py", "premium_client.py", "auth_premium.py", "userbot_fx.py")


def set_bot_instance(bot):
    """Подключает основной TeleBot-инстанс для отправки алертов Создателям."""
    global _bot_instance
    _bot_instance = bot


def _send_alert(chat_id, text):
    global _bot_instance
    try:
        if _bot_instance is None:
            import telebot as _tb
            _bot_instance = _tb.TeleBot(config.TELEGRAM_BOT_TOKEN, parse_mode=None)
        _bot_instance.send_message(chat_id, text, parse_mode="HTML")
        return True
    except Exception as e:
        logger.warning(f"error_diagnostics: alert to {chat_id} failed: {e}")
        return False


def _localize_traceback(tb_str):
    """Ищет самый глубокий кадр внутри файлов проекта. Возвращает (file, line, func)."""
    best = (None, None, None)
    try:
        for line in tb_str.splitlines():
            stripped = line.strip()
            if not stripped.startswith("File "):
                continue
            # Format: File "bot.py", line 1234, in handler
            parts = stripped.split('"')
            if len(parts) < 3:
                continue
            fname = os.path.basename(parts[1])
            if fname in PROJECT_FILES:
                rest = parts[2].strip().lstrip(",").strip()
                line_no = None
                for chunk in rest.split(","):
                    chunk = chunk.strip()
                    if chunk.startswith("line "):
                        try:
                            line_no = int(chunk.split()[1])
                        except (ValueError, IndexError):
                            pass
                func = stripped.split(" in ")[-1].strip() if " in " in stripped else ""
                if line_no is not None:
                    best = (fname, line_no, func)
    except Exception:
        pass
    return best


def _read_code_context(fname, line_no, pad=8):
    """Читает фрагмент исходника вокруг строки ошибки для промпта GLM."""
    try:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), fname)
        if not os.path.exists(path):
            return ""
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        lo = max(0, line_no - 1 - pad)
        hi = min(len(lines), line_no + pad)
        return "".join(f"{i + 1}: {lines[i]}" for i in range(lo, hi))
    except Exception:
        return ""


def _count_occurrences(signature):
    try:
        import sqlite3
        conn = sqlite3.connect(database.DB_PATH, timeout=10.0)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT occurrence_count FROM learning_experience WHERE error_signature = ?", (signature,))
        row = cur.fetchone()
        conn.close()
        return row["occurrence_count"] if row else 1
    except Exception:
        return 1


def get_recent_errors(limit=10):
    """Последние ошибки из журнала learning_experience."""
    try:
        import sqlite3
        conn = sqlite3.connect(database.DB_PATH, timeout=10.0)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute('''SELECT error_type, error_message, traceback_snippet, root_cause, solution,
                              occurrence_count, first_seen, last_seen, context_data
                       FROM learning_experience ORDER BY last_seen DESC LIMIT ?''', (limit,))
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows
    except Exception as e:
        logger.warning(f"error_diagnostics: get_recent_errors failed: {e}")
        return []


def format_errors_report(limit=10):
    """Форматирует журнал ошибок для Telegram (HTML)."""
    rows = get_recent_errors(limit)
    if not rows:
        return f"{PE['check']} <b>Журнал ошибок пуст — сбоев не зафиксировано.</b>"
    lines = [f"{PE['stethoscope']} <b>ЖУРНАЛ ОШИБОК СИСТЕМЫ</b> (последние):", ""]
    for i, r in enumerate(rows, 1):
        loc = _localize_traceback(r.get("traceback_snippet") or "")
        loc_str = f" {PE['pin']} <code>{loc[0]}:{loc[1]}</code>" if loc[0] else ""
        lines.append(
            f"{i}. <b>{html.escape((r.get('error_type') or '?')[:60])}</b>{loc_str}\n"
            f"   {PE['bug']} <code>{html.escape((r.get('error_message') or '')[:160])}</code>\n"
            f"   {PE['repeat']} x{r.get('occurrence_count', 1)} | {PE['clock']} {html.escape(str(r.get('last_seen', ''))[:19])}\n"
            f"   {PE['bulb']} {html.escape((r.get('root_cause') or '')[:120])}"
        )
    lines.append("")
    lines.append(f"{PE['wrench']} <code>!логи анализ</code> — GLM-разбор последней ошибки с готовым патчем")
    return "\n".join(lines)


def build_glm_analysis_prompt(error_row):
    """Собирает промпт для GLM: ошибка + локализация + код вокруг строки."""
    tb = error_row.get("traceback_snippet") or ""
    fname, line_no, func = _localize_traceback(tb)
    code_ctx = _read_code_context(fname, line_no) if fname and line_no else ""
    loc_str = f"{fname}:{line_no} (в функции {func})" if fname else "локализация недоступна"
    return (
        "Ты — Senior Python инженер. Проанализируй ошибку Telegram-бота на telebot (pyTelegramBotAPI) "
        "и выдай диагноз и готовый патч.\n\n"
        f"ТИП ОШИБКИ: {error_row.get('error_type')}\n"
        f"СООБЩЕНИЕ: {error_row.get('error_message')}\n"
        f"КОНТЕКСТ: {error_row.get('context_data') or '-'}\n"
        f"ЛОКАЛИЗАЦИЯ: {loc_str}\n\n"
        f"STACK TRACE (обрезан):\n{tb[:1500]}\n\n"
        f"КОД ВОКРУГ ОШИБКИ ({fname or 'файл неизвестен'}):\n{code_ctx[:4000]}\n\n"
        "ОТВЕТ СТРОГО В ФОРМАТЕ:\n"
        "1. ПЕРВОПРИЧИНА: <одним-двумя предложениями>\n"
        "2. ЛОКАЛИЗАЦИЯ: файл:строка\n"
        "3. ПАТЧ: <исправленный фрагмент кода в блоке ```python ... ``` — только изменённые строки "
        "с парой строк контекста, без пояснений внутри блока>\n"
        "4. ПОЯСНЕНИЕ: <одним предложением, что именно меняет патч>"
    ), loc_str


def analyze_error_with_glm(error_row=None, progress_notifier=None):
    """GLM-5.3 анализ ошибки через Verboo Router. Возвращает текст отчёта."""
    if error_row is None:
        rows = get_recent_errors(1)
        if not rows:
            return "ℹ️ Журнал ошибок пуст — анализировать нечего."
        error_row = rows[0]
    try:
        import self_evolution
        prompt, loc_str = build_glm_analysis_prompt(error_row)
        system_instruction = (
            "Ты — Senior Python инженер по телеграм-ботам на pyTelegramBotAPI. "
            "Отвечай строго по запрошенному формату, лаконично, без воды."
        )
        if progress_notifier:
            try:
                progress_notifier(f"🧠 GLM-5.3 анализирует ошибку ({loc_str})...")
            except Exception:
                pass
        raw = self_evolution.call_glm_self_update(prompt, system_instruction)
        if not raw:
            return ("⚠️ GLM-анализ временно недоступен (Verboo Router не ответил). "
                    f"Локализация ошибки: <code>{html.escape(loc_str)}</code>. Повтори позже командой <code>!логи анализ</code>.")
        return raw.strip()[:3800]
    except Exception as e:
        logger.warning(f"error_diagnostics: GLM analysis failed: {e}")
        return f"⚠️ Ошибка GLM-анализа: {html.escape(str(e)[:200])}"


def _auto_analyze_and_report(signature, error_row):
    """Фоновый авто-анализ новой сигнатуры ошибки через GLM + сохранение в журнал."""
    try:
        report = analyze_error_with_glm(error_row)
        # Сохраняем анализ GLM в базу опыта ошибок для мгновенного доступа по !логи анализ
        try:
            database.record_error_experience(
                error_row.get("error_type", "Error"),
                error_row.get("error_message", ""),
                error_row.get("traceback_snippet", ""),
                context=f"GLM Analysis: {report[:2000]}"
            )
        except Exception as dbe:
            logger.debug(f"record_error_experience notice: {dbe}")
        logger.info(f"error_diagnostics: GLM background analysis completed for {signature[:16]}")
    except Exception as e:
        logger.warning(f"error_diagnostics: auto analysis thread failed: {e}")


class BotExceptionHandler(telebot.ExceptionHandler):
    """Глобальный обработчик необработанных исключений TeleBot (polling + хендлеры)."""

    def handle(self, exception):
        try:
            err_type = type(exception).__name__
            err_msg = str(exception)[:300]
            # Ignore transient 409 Conflict and restart disconnects during Render rolling deploys / container handover
            ign_patterns = [
                "terminated by other getupdates",
                "error code: 409",
                "conflict",
                "409 conflict",
                "connection reset by peer",
                "serverdisconnectederror"
            ]
            if any(p in err_msg.lower() for p in ign_patterns):
                logger.info(f"Ignored transient 409/polling deploy exception: {err_msg[:120]}")
                return True
            tb_str = traceback.format_exception(type(exception), exception, exception.__traceback__)
            tb_str = "".join(tb_str)[:2000]

            fname, line_no, func = _localize_traceback(tb_str)
            loc_str = f"{fname}:{line_no}" if fname else "стек вне файлов проекта"

            # 1. Журнал + эвристическая диагностика первопричины
            signature = database.record_error_experience(
                err_type, err_msg, tb_str, context=f"AutoDiagnostics ({loc_str})"
            ) or f"{err_type}:{err_msg[:40]}"

            occurrences = _count_occurrences(signature)

            # 2. Дедупликация и запуск фонового GLM анализа (без спама в ЛС Создателя)
            now = time.time()
            with _alert_lock:
                last = _last_alert_ts.get(signature, 0.0)
                should_process = (now - last) > ALERT_DEDUPE_WINDOW
                if should_process:
                    _last_alert_ts[signature] = now
                    first_time = occurrences <= 1

            if should_process:
                logger.warning(f"Error diagnostics: {loc_str} -> {err_type}: {err_msg[:200]} (repeats: {occurrences})")

                # 3. Авто-GLM анализ только для новых сигнатур (фоновое самовосстановление)
                with _alert_lock:
                    glm_allowed = (now - _last_glm_ts["ts"]) > GLM_AUTO_ANALYSIS_COOLDOWN
                    if glm_allowed:
                        _last_glm_ts["ts"] = now
                if first_time and glm_allowed:
                    row = {"error_type": err_type, "error_message": err_msg,
                           "traceback_snippet": tb_str, "context_data": loc_str}
                    threading.Thread(target=_auto_analyze_and_report,
                                     args=(signature, row), daemon=True,
                                     name="glm_auto_analysis").start()
        except Exception as meta_err:
            # Обработчик ошибок не имеет права падать сам
            logger.error(f"error_diagnostics: handler meta-error: {meta_err}")
        return True


def get_diagnostics_status():
    """Сводка для панели Создателя."""
    rows = get_recent_errors(100)
    total_unique = database.get_learning_stats().get("total_unique_errors", 0)
    return {
        "unique_errors": total_unique,
        "recent_count": len(rows),
        "last_error": (rows[0]["error_type"] + ": " + (rows[0]["error_message"] or "")[:80]) if rows else "нет",
        "alert_targets": CREATOR_ALERT_IDS,
    }
