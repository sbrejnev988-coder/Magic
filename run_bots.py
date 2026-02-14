#!/usr/bin/env python3
"""
РЎРєСЂРёРїС‚ РґР»СЏ РѕРґРЅРѕРІСЂРµРјРµРЅРЅРѕРіРѕ Р·Р°РїСѓСЃРєР° РІСЃРµС… Р±РѕС‚РѕРІ MysticBot.
Р—Р°РїСѓСЃРєР°РµС‚:
1. РћСЃРЅРѕРІРЅРѕР№ Р±РѕС‚ (bot/main.py)
2. Р‘РѕС‚-РєРѕРЅСЃСѓР»СЊС‚Р°РЅС‚ (admin_bot.py)

РСЃРїРѕР»СЊР·РѕРІР°РЅРёРµ:
    python run_bots.py          # Р·Р°РїСѓСЃРє РІ РєРѕРЅСЃРѕР»Рё
    python run_bots.py --daemon # Р·Р°РїСѓСЃРє РІ С„РѕРЅРµ (РґРµРјРѕРЅ)
"""

import asyncio
import subprocess
import sys
import os
import signal
import time
from pathlib import Path
import logging

# Загрузка переменных окружения из .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# РќР°СЃС‚СЂРѕР№РєР° Р»РѕРіРёСЂРѕРІР°РЅРёСЏ
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler("logs/bots_launcher.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("bots_launcher")

# РџСѓС‚Рё Рє СЃРєСЂРёРїС‚Р°Рј Р±РѕС‚РѕРІ
MAIN_BOT_SCRIPT = "bot/main.py"
CONSULTANT_BOT_SCRIPT = "admin_bot.py"

# РџСЂРѕС†РµСЃСЃС‹ Р±РѕС‚РѕРІ
processes = []


def signal_handler(signum, frame):
    """РћР±СЂР°Р±РѕС‚С‡РёРє СЃРёРіРЅР°Р»РѕРІ РґР»СЏ РєРѕСЂСЂРµРєС‚РЅРѕРіРѕ Р·Р°РІРµСЂС€РµРЅРёСЏ"""
    logger.info(f"РџРѕР»СѓС‡РµРЅ СЃРёРіРЅР°Р» {signum}. РћСЃС‚Р°РЅР°РІР»РёРІР°СЋ Р±РѕС‚РѕРІ...")
    stop_bots()
    sys.exit(0)


def stop_bots():
    """РћСЃС‚Р°РЅРѕРІРєР° РІСЃРµС… Р·Р°РїСѓС‰РµРЅРЅС‹С… Р±РѕС‚РѕРІ"""
    logger.info("РћСЃС‚Р°РЅРѕРІРєР° Р±РѕС‚РѕРІ...")
    for proc in processes:
        if proc and proc.poll() is None:
            logger.info(f"РћСЃС‚Р°РЅР°РІР»РёРІР°СЋ РїСЂРѕС†РµСЃСЃ {proc.pid}...")
            proc.terminate()
            try:
                proc.wait(timeout=5)
                logger.info(f"РџСЂРѕС†РµСЃСЃ {proc.pid} РѕСЃС‚Р°РЅРѕРІР»РµРЅ.")
            except subprocess.TimeoutExpired:
                logger.warning(f"РџСЂРѕС†РµСЃСЃ {proc.pid} РЅРµ РѕСЃС‚Р°РЅРѕРІРёР»СЃСЏ, РїСЂРёРЅСѓРґРёС‚РµР»СЊРЅРѕРµ Р·Р°РІРµСЂС€РµРЅРёРµ...")
                proc.kill()
    
    processes.clear()
    logger.info("Р’СЃРµ Р±РѕС‚С‹ РѕСЃС‚Р°РЅРѕРІР»РµРЅС‹.")


def check_requirements():
    """РџСЂРѕРІРµСЂРєР° РЅР°Р»РёС‡РёСЏ РЅРµРѕР±С…РѕРґРёРјС‹С… С„Р°Р№Р»РѕРІ"""
    required_files = [MAIN_BOT_SCRIPT, CONSULTANT_BOT_SCRIPT, ".env"]
    missing_files = []
    
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        logger.error(f"РћС‚СЃСѓС‚СЃС‚РІСѓСЋС‚ РЅРµРѕР±С…РѕРґРёРјС‹Рµ С„Р°Р№Р»С‹: {missing_files}")
        logger.info("РЈР±РµРґРёС‚РµСЃСЊ, С‡С‚Рѕ РІС‹ РЅР°С…РѕРґРёС‚РµСЃСЊ РІ РєРѕСЂРЅРµРІРѕР№ РїР°РїРєРµ MysticBot.")
        return False
    
    # РџСЂРѕРІРµСЂСЏРµРј РЅР°Р»РёС‡РёРµ РїР°РїРєРё logs
    logs_dir = Path("logs")
    if not logs_dir.exists():
        logs_dir.mkdir(parents=True, exist_ok=True)
        logger.info("РЎРѕР·РґР°РЅР° РїР°РїРєР° logs/ РґР»СЏ С…СЂР°РЅРµРЅРёСЏ Р»РѕРіРѕРІ.")
    
    return True


def start_bot(script_name, bot_name):
    """Р—Р°РїСѓСЃРє РѕРґРЅРѕРіРѕ Р±РѕС‚Р°"""
    try:
        logger.info(f"Р—Р°РїСѓСЃРєР°СЋ {bot_name} ({script_name})...")
        
        # РЎРѕР·РґР°РµРј РѕС‚РґРµР»СЊРЅС‹Р№ Р»РѕРі-С„Р°Р№Р» РґР»СЏ СЌС‚РѕРіРѕ Р±РѕС‚Р°
        log_file = f"logs/{bot_name.lower().replace(' ', '_')}.log"
        
        # РћС‚РєСЂС‹РІР°РµРј Р»РѕРі-С„Р°Р№Р» РґР»СЏ Р·Р°РїРёСЃРё
        with open(log_file, "a", encoding="utf-8") as log_fd:
            # Р—Р°РїСѓСЃРєР°РµРј РїСЂРѕС†РµСЃСЃ
            proc = subprocess.Popen(
                [sys.executable, "-m", script_name.replace(".py", "").replace("/", ".")],
                stdout=log_fd,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                bufsize=1
            )
            
            processes.append(proc)
            logger.info(f"{bot_name} Р·Р°РїСѓС‰РµРЅ (PID: {proc.pid}). Р›РѕРіРё РІ {log_file}")
            
            # Р”Р°РґРёРј РїСЂРѕС†РµСЃСЃСѓ РЅРµРјРЅРѕРіРѕ РІСЂРµРјРµРЅРё РЅР° РёРЅРёС†РёР°Р»РёР·Р°С†РёСЋ
            time.sleep(2)
            
            # РџСЂРѕРІРµСЂРёРј, РЅРµ Р·Р°РІРµСЂС€РёР»СЃСЏ Р»Рё РїСЂРѕС†РµСЃСЃ СЃ РѕС€РёР±РєРѕР№
            if proc.poll() is not None:
                logger.error(f"{bot_name} Р·Р°РІРµСЂС€РёР»СЃСЏ СЃСЂР°Р·Сѓ РїРѕСЃР»Рµ Р·Р°РїСѓСЃРєР°. РџСЂРѕРІРµСЂСЊС‚Рµ Р»РѕРіРё.")
                # РџСЂРѕС‡РёС‚Р°РµРј РїРѕСЃР»РµРґРЅРёРµ СЃС‚СЂРѕРєРё Р»РѕРіР° РґР»СЏ РґРёР°РіРЅРѕСЃС‚РёРєРё
                try:
                    with open(log_file, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                        if lines:
                            logger.error(f"РџРѕСЃР»РµРґРЅРёРµ СЃС‚СЂРѕРєРё Р»РѕРіР°:\n{''.join(lines[-20:])}")
                except:
                    pass
                return False
            
            return True
            
    except Exception as e:
        logger.error(f"РћС€РёР±РєР° РїСЂРё Р·Р°РїСѓСЃРєРµ {bot_name}: {e}")
        return False


def start_all_bots(daemon_mode=False):
    """Р—Р°РїСѓСЃРє РІСЃРµС… Р±РѕС‚РѕРІ"""
    if not check_requirements():
        return False
    
    logger.info("=" * 60)
    logger.info("Р—РђРџРЈРЎРљ Р’РЎР•РҐ Р‘РћРўРћР’ MYSTICBOT")
    logger.info("=" * 60)
    
    # Р РµРіРёСЃС‚СЂРёСЂСѓРµРј РѕР±СЂР°Р±РѕС‚С‡РёРєРё СЃРёРіРЅР°Р»РѕРІ
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Р—Р°РїСѓСЃРєР°РµРј Р±РѕС‚РѕРІ
    bots_to_start = [
        (MAIN_BOT_SCRIPT, "РћСЃРЅРѕРІРЅРѕР№ Р±РѕС‚"),
        (CONSULTANT_BOT_SCRIPT, "Р‘РѕС‚-РєРѕРЅСЃСѓР»СЊС‚Р°РЅС‚")
    ]
    
    success_count = 0
    for script, name in bots_to_start:
        if start_bot(script, name):
            success_count += 1
    
    if success_count == 0:
        logger.error("РќРµ СѓРґР°Р»РѕСЃСЊ Р·Р°РїСѓСЃС‚РёС‚СЊ РЅРё РѕРґРЅРѕРіРѕ Р±РѕС‚Р°.")
        return False
    
    logger.info(f"РЈСЃРїРµС€РЅРѕ Р·Р°РїСѓС‰РµРЅРѕ {success_count}/{len(bots_to_start)} Р±РѕС‚РѕРІ.")
    
    if daemon_mode:
        logger.info("Р РµР¶РёРј РґРµРјРѕРЅР°: Р±РѕС‚С‹ СЂР°Р±РѕС‚Р°СЋС‚ РІ С„РѕРЅРµ.")
        logger.info("Р”Р»СЏ РѕСЃС‚Р°РЅРѕРІРєРё РёСЃРїРѕР»СЊР·СѓР№С‚Рµ Ctrl+C РёР»Рё РѕС‚РїСЂР°РІСЊС‚Рµ SIGTERM.")
        
        # Р’ СЂРµР¶РёРјРµ РґРµРјРѕРЅР° Р¶РґС‘Рј СЃРёРіРЅР°Р»Р° Р·Р°РІРµСЂС€РµРЅРёСЏ (РґР»СЏ Windows РёСЃРїРѕР»СЊР·СѓРµРј Р±РµСЃРєРѕРЅРµС‡РЅС‹Р№ С†РёРєР»)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("РџРѕР»СѓС‡РµРЅ Ctrl+C. РћСЃС‚Р°РЅР°РІР»РёРІР°СЋ Р±РѕС‚РѕРІ...")
            stop_bots()
    
    else:
        logger.info("Р‘РѕС‚С‹ Р·Р°РїСѓС‰РµРЅС‹. Р›РѕРіРё РІС‹РІРѕРґСЏС‚СЃСЏ РІ РєРѕРЅСЃРѕР»СЊ Рё С„Р°Р№Р»С‹ РІ РїР°РїРєРµ logs/.")
        logger.info("Р”Р»СЏ РѕСЃС‚Р°РЅРѕРІРєРё РЅР°Р¶РјРёС‚Рµ Ctrl+C.")
        
        # Р’ РёРЅС‚РµСЂР°РєС‚РёРІРЅРѕРј СЂРµР¶РёРјРµ РїРѕРєР°Р·С‹РІР°РµРј СЃС‚Р°С‚СѓСЃ Рё Р¶РґС‘Рј Ctrl+C
        try:
            while True:
                # РџРµСЂРёРѕРґРёС‡РµСЃРєРё РїСЂРѕРІРµСЂСЏРµРј СЃС‚Р°С‚СѓСЃ Р±РѕС‚РѕРІ
                time.sleep(10)
                
                alive_count = 0
                for i, proc in enumerate(processes):
                    if proc.poll() is None:
                        alive_count += 1
                    else:
                        bot_name = bots_to_start[i][1]
                        logger.warning(f"{bot_name} Р·Р°РІРµСЂС€РёР» СЂР°Р±РѕС‚Сѓ (РєРѕРґ: {proc.returncode}).")
                
                if alive_count == 0:
                    logger.info("Р’СЃРµ Р±РѕС‚С‹ Р·Р°РІРµСЂС€РёР»Рё СЂР°Р±РѕС‚Сѓ.")
                    break
                    
                logger.info(f"Р Р°Р±РѕС‚Р°СЋС‚ Р±РѕС‚РѕРІ: {alive_count}/{len(processes)}")
                
        except KeyboardInterrupt:
            logger.info("\nРџРѕР»СѓС‡РµРЅ Ctrl+C. РћСЃС‚Р°РЅР°РІР»РёРІР°СЋ Р±РѕС‚РѕРІ...")
            stop_bots()
    
    return True


async def start_all_bots_async():
    """РђСЃРёРЅС…СЂРѕРЅРЅС‹Р№ Р·Р°РїСѓСЃРє Р±РѕС‚РѕРІ (Р°Р»СЊС‚РµСЂРЅР°С‚РёРІРЅС‹Р№ РІР°СЂРёР°РЅС‚)"""
    if not check_requirements():
        return False
    
    logger.info("РђСЃРёРЅС…СЂРѕРЅРЅС‹Р№ Р·Р°РїСѓСЃРє Р±РѕС‚РѕРІ...")
    
    # РЎРѕР·РґР°РµРј Р·Р°РґР°С‡Рё РґР»СЏ Р·Р°РїСѓСЃРєР° Р±РѕС‚РѕРІ
    tasks = []
    
    async def run_bot_async(script, name):
        """Р—Р°РїСѓСЃРє Р±РѕС‚Р° РІ Р°СЃРёРЅС…СЂРѕРЅРЅРѕРј СЂРµР¶РёРјРµ"""
        try:
            logger.info(f"Р—Р°РїСѓСЃРєР°СЋ {name}...")
            # Р—Р°РїСѓСЃРєР°РµРј РєР°Рє РїРѕРґРїСЂРѕС†РµСЃСЃ, РЅРѕ СЃ Р°СЃРёРЅС…СЂРѕРЅРЅС‹Рј РѕР¶РёРґР°РЅРёРµРј
            proc = await asyncio.create_subprocess_exec(
                sys.executable, "-m", script.replace(".py", "").replace("/", "."),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                text=True,
                encoding="utf-8"
            )
            
            processes.append(proc)
            logger.info(f"{name} Р·Р°РїСѓС‰РµРЅ (PID: {proc.pid}).")
            
            # Р§РёС‚Р°РµРј РІС‹РІРѕРґ РІ СЂРµР°Р»СЊРЅРѕРј РІСЂРµРјРµРЅРё
            async for line in proc.stdout:
                print(f"[{name}] {line}", end="")
            
            await proc.wait()
            logger.info(f"{name} Р·Р°РІРµСЂС€РёР» СЂР°Р±РѕС‚Сѓ СЃ РєРѕРґРѕРј {proc.returncode}.")
            
        except Exception as e:
            logger.error(f"РћС€РёР±РєР° РїСЂРё Р·Р°РїСѓСЃРєРµ {name}: {e}")
    
    # Р—Р°РїСѓСЃРєР°РµРј Р±РѕС‚РѕРІ
    tasks.append(run_bot_async(MAIN_BOT_SCRIPT, "РћСЃРЅРѕРІРЅРѕР№ Р±РѕС‚"))
    tasks.append(run_bot_async(CONSULTANT_BOT_SCRIPT, "Р‘РѕС‚-РєРѕРЅСЃСѓР»СЊС‚Р°РЅС‚"))
    
    # Р–РґС‘Рј Р·Р°РІРµСЂС€РµРЅРёСЏ РІСЃРµС… Р·Р°РґР°С‡
    await asyncio.gather(*tasks, return_exceptions=True)
    
    return True


def main():
    """РћСЃРЅРѕРІРЅР°СЏ С„СѓРЅРєС†РёСЏ"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Р—Р°РїСѓСЃРє РІСЃРµС… Р±РѕС‚РѕРІ MysticBot")
    parser.add_argument("--daemon", "-d", action="store_true", 
                       help="Р—Р°РїСѓСЃРє РІ С„РѕРЅРѕРІРѕРј СЂРµР¶РёРјРµ (РґРµРјРѕРЅ)")
    parser.add_argument("--async", "-a", action="store_true", dest="async_mode",
                       help="РСЃРїРѕР»СЊР·РѕРІР°С‚СЊ Р°СЃРёРЅС…СЂРѕРЅРЅС‹Р№ Р·Р°РїСѓСЃРє (СЌРєСЃРїРµСЂРёРјРµРЅС‚Р°Р»СЊРЅРѕ)")
    parser.add_argument("--stop", "-s", action="store_true",
                       help="РћСЃС‚Р°РЅРѕРІРёС‚СЊ РІСЃРµ Р·Р°РїСѓС‰РµРЅРЅС‹Рµ Р±РѕС‚С‹")
    
    args = parser.parse_args()
    
    if args.stop:
        # РќР°Р№РґС‘Рј Рё РѕСЃС‚Р°РЅРѕРІРёРј РІСЃРµ РїСЂРѕС†РµСЃСЃС‹ Python, СЃРІСЏР·Р°РЅРЅС‹Рµ СЃ Р±РѕС‚Р°РјРё
        import psutil
        current_pid = os.getpid()
        
        logger.info("РџРѕРёСЃРє РїСЂРѕС†РµСЃСЃРѕРІ Р±РѕС‚РѕРІ...")
        bot_processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = proc.info['cmdline']
                if cmdline and 'python' in proc.info['name'].lower():
                    # РџСЂРѕРІРµСЂСЏРµРј, СЃРІСЏР·Р°РЅ Р»Рё РїСЂРѕС†РµСЃСЃ СЃ РЅР°С€РёРјРё Р±РѕС‚Р°РјРё
                    if any(x in ' '.join(cmdline) for x in ['bot/main', 'admin_bot']):
                        if proc.info['pid'] != current_pid:
                            bot_processes.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        if bot_processes:
            logger.info(f"РќР°Р№РґРµРЅРѕ {len(bot_processes)} РїСЂРѕС†РµСЃСЃРѕРІ Р±РѕС‚РѕРІ:")
            for proc in bot_processes:
                logger.info(f"  PID {proc.info['pid']}: {' '.join(proc.info['cmdline'][:3])}...")
                proc.terminate()
            
            # Р”Р°РґРёРј РїСЂРѕС†РµСЃСЃР°Рј РІСЂРµРјСЏ РЅР° Р·Р°РІРµСЂС€РµРЅРёРµ
            time.sleep(3)
            
            # РџСЂРёРЅСѓРґРёС‚РµР»СЊРЅРѕ Р·Р°РІРµСЂС€Р°РµРј РѕСЃС‚Р°РІС€РёРµСЃСЏ
            for proc in bot_processes:
                if proc.is_running():
                    proc.kill()
                    logger.info(f"РџСЂРёРЅСѓРґРёС‚РµР»СЊРЅРѕ Р·Р°РІРµСЂС€С‘РЅ PID {proc.info['pid']}")
            
            logger.info("Р’СЃРµ РїСЂРѕС†РµСЃСЃС‹ Р±РѕС‚РѕРІ РѕСЃС‚Р°РЅРѕРІР»РµРЅС‹.")
        else:
            logger.info("РџСЂРѕС†РµСЃСЃС‹ Р±РѕС‚РѕРІ РЅРµ РЅР°Р№РґРµРЅС‹.")
        
        return
    
    # Р—Р°РїСѓСЃРє Р±РѕС‚РѕРІ
    if args.async_mode:
        # Р­РєСЃРїРµСЂРёРјРµРЅС‚Р°Р»СЊРЅС‹Р№ Р°СЃРёРЅС…СЂРѕРЅРЅС‹Р№ Р·Р°РїСѓСЃРє
        asyncio.run(start_all_bots_async())
    else:
        # РЎС‚Р°РЅРґР°СЂС‚РЅС‹Р№ Р·Р°РїСѓСЃРє
        start_all_bots(args.daemon)


if __name__ == "__main__":
    main()
