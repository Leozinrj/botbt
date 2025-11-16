# -*- coding: utf-8 -*-
"""
Amazon Cave Bot - Sistema de navegação em caverna com combate inteligente
Prioridades: Inimigos > Loot > Navegação
"""

import serial
import time
import pyautogui as pg
import os
import sys
import numpy as np
from PIL import Image

# ===========================
# CONFIGURAÇÕES
# ===========================
COM_PORT = "COM13"
BAUD_RATE = 115200
CONFIDENCE = 0.8
LOCATE_TIMEOUT = 10.0

# Sistema de healing
HEALING_ENABLED = False
HP_REGION = (9, 7, 497, 7)  # Região da barra de HP

# Desabilita o failsafe do PyAutoGUI
pg.FAILSAFE = False
pg.PAUSE = 0.05

# ===========================
# ESTRUTURA DE ROTAS
# ===========================

# Parte Superior - 7 flags com delays específicos
UPPER_ROUTE = [
    ("am_a1", 0),   # Início - sem delay inicial
    ("am_a2", 8),   # 8 segundos
    ("am_a3", 9),   # 9 segundos
    ("am_a4", 7),   # 7 segundos
    ("am_a5", 5),   # 5 segundos
    ("am_a6", 5),   # 5 segundos
    ("am_a7", 2),   # Descida no buraco - 2 segundos
]

# Subterrâneo - Rota completa
UNDERGROUND_ROUTE = [
    ("am_s1", 2),   # 2 segundos
    ("am_s2", 5),   # 5 segundos
    ("am_s3", 6),   # 6 segundos
    ("am_s4", 6),   # 6 segundos
    ("am_s5", 6),   # 6 segundos
    ("am_s6", 6),   # 6 segundos
    ("am_s7", 7),   # 7 segundos
    ("am_s8", 13),  # 13 segundos
    ("am_s9", 12),  # 12 segundos
    ("am_s10", 8),  # 8 segundos
    ("am_s11", 14), # 14 segundos
    ("am_s6", 6),   # Volta para s6 - 6 segundos
    ("am_s5", 4),   # Volta para s5 - 4 segundos
    ("am_s4", 6),   # Volta para s4 - 6 segundos
    ("am_s12", 7),  # 7 segundos
    ("am_s13", 7),  # 7 segundos
    ("am_s14", 5),  # 5 segundos
    ("subida1", 2),  # Subida - 2 segundos
]

# Prioridades de inimigos (quanto maior, maior prioridade)
ENEMY_PRIORITY = {
    "witch": 3,      # Prioridade alta
    "valkyrie": 2,   # Prioridade média
    "amazon": 1,     # Prioridade comum
}

COMBAT_DELAY = 7.0  # Tempo médio de combate (reduzido de 8.0 para 7.0)
LOOT_CHECK_TIME = 1.3  # Tempo para verificar loot após combate (reduzido de 1.5 para 1.3)

# ===========================
# FUNÇÕES DE COMUNICAÇÃO SERIAL
# ===========================

def send_command(ser, cmd):
    """Envia comando para Arduino e aguarda resposta OK"""
    try:
        ser.write(f"{cmd}\n".encode('utf-8'))
        ser.flush()
        time.sleep(0.1)
        return True
    except Exception as e:
        print(f"[ERRO] Falha ao enviar comando: {e}")
        return False

def wait_exact(seconds, description=""):
    """Espera exata com descrição opcional"""
    if description:
        print(f"[WAIT] {description} ({seconds:.1f}s)")
    time.sleep(seconds)

def move_mouse(ser, x, y):
    """Move o mouse para posição absoluta usando PyAutoGUI"""
    try:
        pg.moveTo(x, y, duration=0.1)
        # Envia comando ao Arduino apenas para sincronizar
        send_command(ser, f"MA {x} {y}")
        return True
    except Exception as e:
        print(f"[ERRO] Falha ao mover mouse: {e}")
        return False

def click_mouse(ser):
    """Clica com botão esquerdo"""
    return send_command(ser, "CL")

def right_click_mouse(ser):
    """Clica com botão direito"""
    return send_command(ser, "CR")

def click_at_position(ser, x, y, right_click=False):
    """Move e clica em uma posição (esquerdo ou direito)"""
    print(f"[MOUSE] Movendo para ({x},{y})")
    if move_mouse(ser, x, y):
        time.sleep(0.1)
        if right_click:
            if send_command(ser, "CR"):
                print(f"[MOUSE] Clique DIREITO executado em ({x},{y})")
                return True
        else:
            if click_mouse(ser):
                print(f"[MOUSE] Clique ESQUERDO executado em ({x},{y})")
                return True
    return False

def move_to_screen_center(ser):
    """Move o mouse para o centro da tela"""
    screen_width, screen_height = pg.size()
    center_x = screen_width // 2
    center_y = screen_height // 2
    print(f"[MOUSE] Movendo para centro da tela ({center_x},{center_y})")
    pg.moveTo(center_x, center_y, duration=0.1)
    return True

def press_bracket(ser):
    """Pressiona tecla 9 duas vezes após matar inimigo"""
    print("[TECLADO] Pressionando 9 (1ª vez)")
    send_command(ser, "KT 9")
    time.sleep(0.2)
    print("[TECLADO] Pressionando 9 (2ª vez)")
    send_command(ser, "KT 9")
    return True

def press_key_3(ser):
    """Pressiona tecla 3 para healing"""
    print("[HEALING] Pressionando tecla 3")
    return send_command(ser, "KT 3")

# ===========================
# SISTEMA DE DETECÇÃO DE HP
# ===========================

def get_hp_by_color_detection():
    """
    Detecta HP baseado nas cores
    Retorna: 'full', 'high', 'medium', 'low', 'unknown'
    """
    try:
        x, y, width, height = HP_REGION
        screenshot = pg.screenshot(region=(x, y, width, height))
        img_array = np.array(screenshot)
        
        total_pixels = 0
        full_hp_pixels = 0
        hp80_pixels = 0
        medium_hp_pixels = 0
        low_hp_pixels = 0
        
        for py in range(height):
            for px in range(width):
                try:
                    b, g, r = img_array[py, px][:3]
                    
                    if r < 50 and g < 50 and b < 50:
                        continue
                        
                    total_pixels += 1
                    
                    # HP cheio - Verde intenso
                    if g > 150 and r < 100 and b < 100 and g > r + 30:
                        full_hp_pixels += 1
                    # HP 80% - Verde musgo
                    elif g > 120 and r > 80 and r < 140 and b < 80 and g > r:
                        hp80_pixels += 1
                    # HP médio - Amarelo/laranja
                    elif (r > 120 and g > 90 and b < 100 and r >= g) or \
                         (r > 100 and g > 80 and b < 80 and r > g - 10) or \
                         (r + g > 180 and b < 100 and abs(r - g) < 60):
                        medium_hp_pixels += 1
                    # HP baixo - Vermelho
                    elif r > 150 and g < 100 and b < 100 and r > g + 50:
                        low_hp_pixels += 1
                except (IndexError, ValueError):
                    continue
        
        if total_pixels == 0:
            return "unknown"
        
        full_ratio = full_hp_pixels / total_pixels
        hp80_ratio = hp80_pixels / total_pixels
        medium_ratio = medium_hp_pixels / total_pixels
        low_ratio = low_hp_pixels / total_pixels
        
        # Determina estado do HP
        if full_ratio > 0.3:
            return "full"
        elif hp80_ratio > 0.3:
            return "high"
        elif medium_ratio > 0.01 or (total_pixels > 1000 and medium_ratio > 0.005):
            return "medium"
        elif low_ratio > 0.1:
            return "low"
        elif total_pixels > 500 and full_ratio < 0.8 and hp80_ratio < 0.2:
            return "medium"
        else:
            return "unknown"
            
    except Exception as e:
        print(f"[HEALING] Erro na detecção de HP: {e}")
        return "unknown"

def check_and_heal(ser):
    """Verifica HP e faz healing se necessário"""
    if not HEALING_ENABLED:
        return False
    
    try:
        hp_state = get_hp_by_color_detection()
        
        if hp_state == "medium":
            print(f"[HEALING] *** HP MÉDIO DETECTADO! *** Enviando tecla 3...")
            if press_key_3(ser):
                print(f"[HEALING] ✅ Tecla 3 enviada com SUCESSO!")
                time.sleep(0.5)
                return True
        
        return False
    except Exception as e:
        print(f"[HEALING] ERRO: {e}")
        return False

# ===========================
# SISTEMA DE DETECÇÃO DE IMAGENS
# ===========================

def locate_image(image_path, timeout=LOCATE_TIMEOUT, confidence=CONFIDENCE):
    """Localiza imagem na tela com timeout"""
    filename = os.path.basename(image_path)
    if not os.path.exists(image_path):
        return None
    
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            pos = pg.locateCenterOnScreen(image_path, confidence=confidence)
            if pos:
                return (int(pos.x), int(pos.y))
        except:
            pass
        time.sleep(0.1)
    return None

def find_image_quick(image_path, confidence=0.8):
    """Busca rápida de imagem sem timeout longo"""
    try:
        pos = pg.locateCenterOnScreen(image_path, confidence=confidence)
        if pos:
            return (int(pos.x), int(pos.y))
    except:
        pass
    return None

# ===========================
# SISTEMA DE PRIORIDADE DE INIMIGOS
# ===========================

def check_enemies_on_screen(enemy_images):
    """
    Verifica todos os inimigos na tela e retorna o de maior prioridade
    Retorna: (enemy_name, position, priority) ou None
    """
    enemies_found = []
    
    for enemy_name, enemy_image in enemy_images.items():
        pos = find_image_quick(enemy_image, confidence=0.8)
        if pos:
            priority = ENEMY_PRIORITY.get(enemy_name, 0)
            enemies_found.append((enemy_name, pos, priority))
    
    if not enemies_found:
        return None
    
    # Retorna o inimigo com maior prioridade
    enemies_found.sort(key=lambda x: x[2], reverse=True)
    return enemies_found[0]

# ===========================
# SISTEMA DE LOOT
# ===========================

def check_and_collect_loot(ser, loot_images):
    """
    Verifica se há loot na tela e coleta com CLIQUE DIREITO
    Tenta até 2 vezes se necessário
    Retorna True se coletou loot
    """
    print(f"[LOOT] Verificando loot na tela ({LOOT_CHECK_TIME:.1f}s)...")
    start_time = time.time()
    attempts = 0
    max_attempts = 2
    
    while time.time() - start_time < LOOT_CHECK_TIME and attempts < max_attempts:
        for loot_name, loot_image in loot_images.items():
            pos = find_image_quick(loot_image, confidence=0.7)
            if pos:
                attempts += 1
                print(f"[LOOT] {loot_name.upper()} encontrado em {pos}! (tentativa {attempts}/{max_attempts})")
                print(f"[LOOT] Coletando com CLIQUE DIREITO...")
                if click_at_position(ser, pos[0], pos[1], right_click=True):
                    print(f"[LOOT] ✅ {loot_name.upper()} coletado!")
                    time.sleep(0.5)
                    
                    # Verifica se ainda há mais loot
                    time.sleep(0.3)
                    remaining_loot = False
                    for check_loot_name, check_loot_image in loot_images.items():
                        if find_image_quick(check_loot_image, confidence=0.7):
                            print(f"[LOOT] Ainda há {check_loot_name.upper()} na tela!")
                            remaining_loot = True
                            break
                    
                    if remaining_loot:
                        continue  # Continua coletando
                    else:
                        return True  # Todo loot coletado
        
        time.sleep(0.1)
    
    print("[LOOT] Nenhum loot encontrado ou tempo esgotado")
    return False

# ===========================
# SISTEMA DE COMBATE
# ===========================

def combat_loop(ser, enemy_images, loot_images):
    """
    Loop de combate inteligente com prioridades
    Clica com BOTÃO ESQUERDO nos inimigos
    SEMPRE coleta loot antes de procurar próximo inimigo
    Retorna quando não houver mais inimigos
    """
    combat_count = 0
    consecutive_no_enemies = 0
    
    print("[COMBAT] Iniciando combate...")
    
    while True:
        # Busca inimigo com maior prioridade
        enemy_found = check_enemies_on_screen(enemy_images)
        
        if enemy_found:
            enemy_name, pos, priority = enemy_found
            combat_count += 1
            consecutive_no_enemies = 0
            
            print(f"[COMBAT] {enemy_name.upper()} detectado (prioridade {priority}) em {pos}")
            print(f"[COMBAT] Atacando #{combat_count} com CLIQUE ESQUERDO...")
            
            # Clica no inimigo com BOTÃO ESQUERDO
            if click_at_position(ser, pos[0], pos[1], right_click=False):
                print(f"[COMBAT] {enemy_name.upper()} atacado!")
                
                # Aguarda tempo de combate
                print(f"[COMBAT] Aguardando {COMBAT_DELAY}s de combate...")
                time.sleep(COMBAT_DELAY)
                
                # Pressiona 9 DUAS VEZES após matar
                print(f"[COMBAT] Pressionando tecla 9 (2x) após matar {enemy_name}")
                press_bracket(ser)
                time.sleep(0.2)  # Reduzido de 0.3 para 0.2
                
                # SEMPRE verifica e coleta loot com CLIQUE DIREITO
                # Aguarda até clicar no loot ou tempo esgotar
                loot_collected = check_and_collect_loot(ser, loot_images)
                
                if loot_collected:
                    print(f"[COMBAT] Loot coletado! Aguardando 0.3s antes de procurar próximo inimigo...")
                    time.sleep(0.3)  # Reduzido de 0.5 para 0.3
                else:
                    print(f"[COMBAT] Nenhum loot encontrado. Continuando para próximo inimigo...")
                    time.sleep(0.2)  # Reduzido de 0.3 para 0.2
                
                # Agora sim, procura próximo inimigo
                continue
                
        else:
            consecutive_no_enemies += 1
            print(f"[COMBAT] Nenhum inimigo detectado ({consecutive_no_enemies}/2)")
            
            if consecutive_no_enemies >= 2:
                print(f"[COMBAT] Área limpa! Total de combates: {combat_count}")
                return combat_count
            
            time.sleep(1.0)

# ===========================
# SISTEMA DE NAVEGAÇÃO COM INTERRUPÇÃO
# ===========================

def navigate_to_flag(ser, flag_name, flag_image, delay_after, enemy_images, loot_images):
    """
    Navega para uma flag com sistema de interrupção por inimigos
    Se interrompido, retoma a navegação
    """
    action_completed = False
    attempt_count = 0
    
    while not action_completed and attempt_count < 3:
        attempt_count += 1
        print(f"\n[NAV] Navegando para {flag_name} (tentativa {attempt_count}/3)...")
        
        # Durante busca da flag, verifica inimigos
        enemy_found = check_enemies_on_screen(enemy_images)
        if enemy_found:
            enemy_name, pos, priority = enemy_found
            print(f"[INTERRUPT] {enemy_name.upper()} detectado durante navegação para {flag_name}!")
            print(f"[INTERRUPT] Parando navegação para combater...")
            
            # Entra em combate até limpar área
            combat_loop(ser, enemy_images, loot_images)
            
            print(f"[INTERRUPT] *** RETOMANDO NAVEGAÇÃO PARA {flag_name} ***")
            continue  # Retoma do início
        
        # Procura a flag
        pos = locate_image(flag_image, timeout=5.0, confidence=0.8)
        
        if not pos:
            # Tenta com confidence menor
            pos = locate_image(flag_image, timeout=5.0, confidence=0.7)
        
        if not pos:
            print(f"[NAV] {flag_name} não encontrada!")
            action_completed = True  # Pula para próxima
            break
        
        print(f"[NAV] {flag_name} encontrada em {pos}")
        
        # Clica na flag com BOTÃO ESQUERDO
        if click_at_position(ser, pos[0], pos[1], right_click=False):
            print(f"[NAV] ✅ Clique ESQUERDO em {flag_name} bem-sucedido!")
            
            # Move mouse para centro da tela
            move_to_screen_center(ser)
            time.sleep(0.1)
            
            # Delay após clicar na flag COM MONITORAMENTO (reduzido em 45%)
            if delay_after > 0:
                reduced_delay = delay_after * 0.55  # 45% de redução
                print(f"[NAV] Aguardando {reduced_delay:.1f}s após {flag_name} (reduzido 45%, com monitoramento)...")
                was_interrupted = monitored_delay(ser, reduced_delay, flag_name, enemy_images, loot_images)
                
                if was_interrupted:
                    print(f"[NAV] *** DELAY INTERROMPIDO! RETOMANDO {flag_name} ***")
                    continue  # Retoma do início desta flag
            
            action_completed = True
        else:
            print(f"[NAV] Falha ao clicar em {flag_name}")
            time.sleep(1.0)
    
    return action_completed

def monitored_delay(ser, seconds, context, enemy_images, loot_images):
    """
    Delay com monitoramento de inimigos
    Retorna True se foi interrompido
    """
    start_time = time.time()
    end_time = start_time + seconds
    check_interval = 0.25  # Reduzido de 0.3 para 0.25
    
    enemies_found = 0
    
    while time.time() < end_time:
        # Verifica inimigos
        enemy_found = check_enemies_on_screen(enemy_images)
        if enemy_found:
            enemy_name, pos, priority = enemy_found
            enemies_found += 1
            remaining = end_time - time.time()
            
            print(f"[INTERRUPT] {enemy_name.upper()} detectado durante delay de {context}!")
            print(f"[INTERRUPT] Pausando delay (restavam {remaining:.1f}s)...")
            
            # Entra em combate
            combat_loop(ser, enemy_images, loot_images)
            
            print(f"[INTERRUPT] Retomando delay de {context}...")
            return True  # Indica que foi interrompido
        
        # Pequena pausa
        remaining = max(0, end_time - time.time())
        sleep_time = min(check_interval, remaining)
        if sleep_time > 0:
            time.sleep(sleep_time)
    
    return False  # Não foi interrompido

# ===========================
# LOOP PRINCIPAL
# ===========================

def main_loop(ser):
    """Loop principal do bot"""
    
    # Carrega imagens dos inimigos
    enemy_images = {
        "witch": os.path.abspath(os.path.join("..", "enemy", "witch.png")),
        "valkyrie": os.path.abspath(os.path.join("..", "enemy", "valkyrie.png")),
        "amazon": os.path.abspath(os.path.join("..", "enemy", "amazon.png")),
    }
    
    # Carrega imagens de loot
    loot_images = {
        "loot1": os.path.abspath(os.path.join("..", "loot", "am_loot1.png")),
        "loot2": os.path.abspath(os.path.join("..", "loot", "am_loot2.png")),
        "loot3": os.path.abspath(os.path.join("..", "loot", "am_loot3.png")),
    }
    
    # Verifica se imagens existem
    print("\n[DEBUG] Verificando imagens de inimigos...")
    for name, path in enemy_images.items():
        if os.path.exists(path):
            print(f"[DEBUG] {name}: {path} ✓")
        else:
            print(f"[WARN] {name}: {path} ✗ (não encontrado)")
    
    print("\n[DEBUG] Verificando imagens de loot...")
    for name, path in loot_images.items():
        if os.path.exists(path):
            print(f"[DEBUG] {name}: {path} ✓")
        else:
            print(f"[WARN] {name}: {path} ✗ (não encontrado)")
    
    cycle = 1
    
    while True:
        try:
            print("\n" + "="*60)
            print(f"AMAZON CAVE CYCLE #{cycle}")
            print("="*60)
            
            # ========== PARTE SUPERIOR ==========
            print("\n[PHASE] PARTE SUPERIOR - 7 FLAGS")
            for flag_name, delay_after in UPPER_ROUTE:
                flag_image = os.path.abspath(os.path.join("..", "flags", "amazon_camp", f"{flag_name}.png"))
                navigate_to_flag(ser, flag_name, flag_image, delay_after, enemy_images, loot_images)
            
            print("\n[PHASE] ✅ Parte superior completada!")
            
            # ========== SUBTERRÂNEO ==========
            print("\n[PHASE] SUBTERRÂNEO - ROTA COMPLETA")
            for flag_name, delay_after in UNDERGROUND_ROUTE:
                flag_image = os.path.abspath(os.path.join("..", "flags", "amazon_camp", f"{flag_name}.png"))
                navigate_to_flag(ser, flag_name, flag_image, delay_after, enemy_images, loot_images)
            
            print("\n[PHASE] ✅ Subterrâneo completado!")
            
            # ========== VOLTA PARA FLAG 1 ==========
            print("\n[PHASE] VOLTANDO PARA FLAG 1...")
            flag1_image = os.path.abspath(os.path.join("..", "flags", "amazon_camp", "am_a1.png"))
            navigate_to_flag(ser, "am_a1", flag1_image, 10, enemy_images, loot_images)
            
            print(f"\n[OK] Cycle #{cycle} completo!")
            cycle += 1
            
            time.sleep(3.0)  # Pausa entre ciclos
            
        except KeyboardInterrupt:
            print("\n[STOP] Ctrl+C - Parando bot...")
            break
        except Exception as e:
            print(f"\n[ERRO] {e}")
            import traceback
            traceback.print_exc()
            time.sleep(5.0)

# ===========================
# MAIN
# ===========================

def main():
    print("\n" + "="*60)
    print("AMAZON CAVE BOT - Sistema Inteligente de Prioridades")
    print("="*60)
    print(f"\n[SERIAL] Conectando {COM_PORT} @ {BAUD_RATE}...")
    
    print("\nConfigurações:")
    print("- Parte Superior: 7 flags (am_a1 até am_a7)")
    print("- Subterrâneo: 18 flags (rota completa)")
    print("- Inimigos: witch (prioridade alta), valkyrie (média), amazon (comum)")
    print(f"- Combate: {COMBAT_DELAY}s por inimigo (otimizado)")
    print(f"- Loot: verificação de {LOOT_CHECK_TIME}s")
    print("- Sistema de prioridades: Inimigos > Loot > Navegação")
    print("- Clique ESQUERDO para inimigos e flags")
    print("- Clique DIREITO para loot")
    print("- Tecla 9 (2x) após matar inimigo")
    print("- Delays entre flags: -45% (ultra otimizado)")
    print("- Mouse move para centro após clicar em flag")
    print("- Healing: DESATIVADO")
    
    input("\nENTER para iniciar...")
    
    try:
        with serial.Serial(COM_PORT, BAUD_RATE, timeout=1) as ser:
            print(f"[OK] Conectado em {COM_PORT}")
            print("[SERIAL] Aguardando Arduino...")
            time.sleep(2.0)
            ser.reset_input_buffer()
            print("[OK] Arduino pronto!\n")
            
            main_loop(ser)
    except serial.SerialException as e:
        print(f"[ERRO] Serial: {e}")
    except KeyboardInterrupt:
        print("\n[STOP] Programa interrompido")

if __name__ == "__main__":
    # Desativa aceleração do mouse do Windows
    try:
        import ctypes
        ctypes.windll.user32.SystemParametersInfoA(0x0071, 0, 0, 0)
        print("[MOUSE] Aceleração desativada!")
    except:
        pass
    
    main()
