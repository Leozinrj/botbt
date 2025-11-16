# -*- coding: utf-8 -*-
"""
A22929mazon Cave Bot - Sistema de navegação em caverna com combate inteligente
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

# Define velocidade do mouse (máxima)
pg.PAUSE = 0.001  # EXTREMAMENTE RÁPIDO - quase instantâneo

# ===========================
# ESTRUTURA DE ROTAS
# ===========================

# Parte Superior - 7 flags com delays PADRONIZADOS
UPPER_ROUTE = [
    ("am_a1", 0),   # Início - sem delay inicial
    ("am_a2", 5),   # 5 segundos (era 8)
    ("am_a3", 5),   # 5 segundos (era 9)
    ("am_a4", 5),   # 5 segundos (era 7)
    ("am_a5", 5),   # 5 segundos
    ("am_a6", 5),   # 5 segundos
    ("am_a7", 5),   # 5 segundos (era 2)
]

# Subterrâneo - Rota completa com delays PADRONIZADOS
UNDERGROUND_ROUTE = [
    ("am_s1", 5),   # 5 segundos (era 2)
    ("am_s2", 5),   # 5 segundos
    ("am_s3", 5),   # 5 segundos (era 6)
    ("am_s4", 5),   # 5 segundos (era 6)
    ("am_s5", 5),   # 5 segundos (era 6)
    ("am_s6", 5),   # 5 segundos (era 6)
    ("am_s7", 5),   # 5 segundos (era 7)
    ("am_s8", 5),   # 5 segundos (era 13)
    ("am_s9", 5),   # 5 segundos (era 12)
    ("am_s10", 5),  # 5 segundos (era 8)
    ("am_s11", 5),  # 5 segundos (era 14)
    ("am_s6", 5),   # Volta para s6 - 5 segundos (era 6)
    ("am_s5", 5),   # Volta para s5 - 5 segundos (era 4)
    ("am_s4", 5),   # Volta para s4 - 5 segundos (era 6)
    ("am_s12", 5),  # 5 segundos (era 7)
    ("am_s13", 5),  # 5 segundos (era 7)
    ("am_s14", 5),  # 5 segundos
    ("subida1", 5),  # Subida - 5 segundos (era 2)
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

def press_key_2(ser):
    """Pressiona tecla 2 para healing/ataque especial contra witch"""
    print("[TECLADO] Pressionando tecla 2")
    return send_command(ser, "KT 2")

def press_bracket(ser):
    """Pressiona tecla 9 UMA VEZ após matar inimigo (otimizado)"""
    print("[TECLADO] Pressionando 9 (1x apenas)")
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

def find_image_ULTRA_FAST(image_path, confidence=0.75):
    """Busca ULTRA RÁPIDA de imagem otimizada para inimigos"""
    try:
        # Usa região menor e mais rápida para inimigos (área central da tela)
        region = (300, 200, 700, 400)  # Área central onde inimigos geralmente aparecem
        pos = pg.locateCenterOnScreen(image_path, confidence=confidence, region=region)
        if pos:
            return (int(pos.x), int(pos.y))
    except:
        # Se falhou na região, tenta tela inteira com confidence ainda menor
        try:
            pos = pg.locateCenterOnScreen(image_path, confidence=confidence-0.05)
            if pos:
                return (int(pos.x), int(pos.y))
        except:
            pass
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

def is_in_battle(battle_images):
    """
    Verifica se ESTÁ em batalha (battle_*.png na tela)
    Retorna True se está em batalha, False se não está
    """
    for battle_name, battle_image in battle_images.items():
        try:
            pos = pg.locateCenterOnScreen(battle_image, confidence=0.6)
            if pos:
                return True  # Está em batalha
        except:
            continue
    return False  # NÃO está em batalha

def find_enemy_simple(enemy_images):
    """
    Encontra um inimigo na tela - SIMPLES
    Retorna (nome, posicao) ou (None, None)
    """
    # WITCH primeiro (prioridade)
    if 'witch' in enemy_images:
        try:
            pos = pg.locateCenterOnScreen(enemy_images['witch'], confidence=0.6)
            if pos:
                return 'witch', (pos.x, pos.y)
        except:
            pass
    
    # VALKYRIE
    if 'valkyrie' in enemy_images:
        try:
            pos = pg.locateCenterOnScreen(enemy_images['valkyrie'], confidence=0.6)
            if pos:
                return 'valkyrie', (pos.x, pos.y)
        except:
            pass
    
    # AMAZON
    if 'amazon' in enemy_images:
        try:
            pos = pg.locateCenterOnScreen(enemy_images['amazon'], confidence=0.6)
            if pos:
                return 'amazon', (pos.x, pos.y)
        except:
            pass
    
    return None, None

def combat_system_independent(ser, enemy_images, loot_images, battle_images):
    """
    SISTEMA DE COMBATE INDEPENDENTE
    1. Procura enemy na tela
    2. Verifica se JÁ está em batalha
    3. Se não está, ataca
    4. Se está, aguarda terminar
    """
    enemy_name, enemy_pos = find_enemy_simple(enemy_images)
    
    if not enemy_name:
        return False  # Nenhum enemy encontrado
    
    print(f"[COMBAT] 🎯 {enemy_name.upper()} detectado em ({int(enemy_pos[0])}, {int(enemy_pos[1])})")
    
    # Verifica se JÁ está em batalha
    if is_in_battle(battle_images):
        print(f"[COMBAT] ⏳ JÁ em batalha - aguardando terminar...")
        
        # Aguarda a batalha terminar (battle_*.png sair da tela)
        while is_in_battle(battle_images):
            time.sleep(0.1)
        
        print(f"[COMBAT] ✅ Batalha terminada!")
        
    else:
        print(f"[COMBAT] ⚔️ NÃO em batalha - ATACANDO!")
        
        # Clica no enemy
        click_at_position(ser, enemy_pos[0], enemy_pos[1], right_click=False)
        
        # Se é witch, combate especial
        if enemy_name == 'witch':
            print(f"[COMBAT] 🧙‍♀️ Witch especial - 2x tecla 2")
            press_key_2(ser)
            time.sleep(1.5)
            press_key_2(ser)
            time.sleep(1.0)
        else:
            # Aguarda batalha normal terminar
            print(f"[COMBAT] ⏳ Aguardando batalha {enemy_name}...")
            time.sleep(0.5)  # Aguarda entrar em batalha
            while is_in_battle(battle_images):
                time.sleep(0.1)
    
    # Pressiona 9 e coleta loot
    press_bracket(ser)
    collect_loot_simple(ser, loot_images)
    
    return True  # Combate realizado

def collect_loot_simple(ser, loot_images):
    """Coleta loot SIMPLES - primeiro que achar"""
    time.sleep(0.3)  # Aguarda loot aparecer
    
    for loot_name, loot_image in loot_images.items():
        try:
            pos = pg.locateCenterOnScreen(loot_image, confidence=0.6)
            if pos:
                click_at_position(ser, pos.x, pos.y, right_click=True)
                print(f"[LOOT] ✅ {loot_name} coletado")
                return
        except:
            continue
    print(f"[LOOT] ❌ Nenhum loot encontrado")

# ===========================

def check_enemies_on_screen(enemy_images):
    """
    Verifica todos os inimigos na tela e retorna o de maior prioridade
    OTIMIZADO: Confidence mais baixa para detecção mais agressiva
    Retorna: (enemy_name, position, priority) ou None
    """
    enemies_found = []
    
    for enemy_name, enemy_image in enemy_images.items():
        pos = find_image_quick(enemy_image, confidence=0.60)  # Reduzido de 0.75 para 0.60 - MUITO mais agressivo
        if pos:
            priority = ENEMY_PRIORITY.get(enemy_name, 0)
            enemies_found.append((enemy_name, pos, priority))
    
    if not enemies_found:
        return None
    
    # Retorna o inimigo com maior prioridade
    enemies_found.sort(key=lambda x: x[2], reverse=True)
    return enemies_found[0]

# ===========================
# SISTEMA DE DETECÇÃO GLOBAL
# ===========================

def check_for_immediate_combat(ser, enemy_images, loot_images, battle_images):
    """
    SISTEMA INDEPENDENTE: Usa o novo sistema de combate simplificado
    """
    return combat_system_independent(ser, enemy_images, loot_images, battle_images)

# ===========================
# SISTEMA DE DETECÇÃO DE BATALHA
# ===========================

def wait_for_battle_end(ser, enemy_type, battle_images, max_wait_time=15.0):
    """
    Aguarda o fim da batalha detectando quando a borda vermelha DESAPARECE
    enemy_type: "witch", "valkyrie" ou "amazon"
    Retorna True quando a batalha termina, False se timeout
    ULTRA OTIMIZADO: Detecção mais rápida e agressiva
    """
    battle_key = f"battle_{enemy_type}"
    if battle_key not in battle_images:
        print(f"[BATTLE] ⚠️ Imagem de batalha para {enemy_type} não encontrada! Usando delay fixo...")
        time.sleep(6.0)  # Delay menor
        return True
    
    battle_image = battle_images[battle_key]
    print(f"[BATTLE] 🔍 Aguardando fim da batalha contra {enemy_type.upper()}...")
    print(f"[BATTLE] ⚡ Detecção ULTRA RÁPIDA da borda vermelha...")
    
    start_time = time.time()
    check_interval = 0.05  # ULTRA OTIMIZADO: 50ms (era 80ms)
    battle_detected = False
    
    while time.time() - start_time < max_wait_time:
        # ULTRA RÁPIDA: Procura pela borda vermelha com confidence BAIXA
        pos = locate_image(battle_image, timeout=0.2, confidence=0.50)  # Reduzido de 0.55 para 0.50
        
        if pos and not battle_detected:
            # Primeira detecção da batalha
            battle_detected = True
            elapsed = time.time() - start_time
            print(f"[BATTLE] ⚔️ Batalha CONFIRMADA após {elapsed:.1f}s - Borda vermelha detectada!")
        elif not pos and battle_detected:
            # Borda vermelha DESAPARECEU = Batalha terminou!
            elapsed = time.time() - start_time
            print(f"[BATTLE] ✅ Batalha CONCLUÍDA em {elapsed:.1f}s - Borda desapareceu!")
            return True
        elif not pos and not battle_detected:
            # Ainda não detectou o início da batalha
            elapsed = time.time() - start_time
            if elapsed > 2.0:  # REDUZIDO: Menos tempo para detectar (era 3.0s)
                print(f"[BATTLE] ⚠️ Batalha não detectada após {elapsed:.1f}s - Tentando confidence ULTRA baixa...")
                # TENTATIVA ULTRA BAIXA: Confidence extremamente baixa
                pos_ultra_low = locate_image(battle_image, timeout=0.1, confidence=0.40)  # Confidence MUITO baixa
                if pos_ultra_low:
                    battle_detected = True
                    print(f"[BATTLE] ⚔️ Batalha detectada com confidence ULTRA BAIXA (0.40)!")
                else:
                    print(f"[BATTLE] ⚠️ Usando fallback - tempo de segurança reduzido...")
                    time.sleep(3.0)  # Tempo de segurança menor (era 4.0s)
                    return True
        
        time.sleep(check_interval)
    
    # Timeout - forçar término
    print(f"[BATTLE] ⏰ Timeout após {max_wait_time}s - Forçando término da batalha")
    return True

# ===========================
# SISTEMA DE LOOT
# ===========================

def check_and_collect_loot_SINGLE(ser, loot_images):
    """
    Versão ÚNICA da coleta de loot - Clica APENAS 1x após batalha
    Encontra o PRIMEIRO loot disponível e clica DIREITO
    Retorna True se coletou loot
    """
    print(f"[LOOT] 🎯 SINGLE MODE - 1 clique apenas")
    print(f"[LOOT] ⏳ Aguardando loot aparecer (0.6s)...")
    time.sleep(0.6)  # Tempo reduzido
    
    # Busca o PRIMEIRO loot encontrado
    for loot_name, loot_image in loot_images.items():
        pos = find_image_ULTRA_FAST(loot_image, confidence=0.60)
        if pos:
            print(f"[LOOT] 🎯 PRIMEIRO loot encontrado: {loot_name.upper()} em {pos}")
            print(f"[LOOT] 🖱️ Clicando DIREITO apenas 1x...")
            
            if click_at_position(ser, pos[0], pos[1], right_click=True):
                print(f"[LOOT] ✅ Loot coletado com sucesso!")
                print(f"[LOOT] ⏳ Aguardando 1.0s antes da próxima batalha...")
                time.sleep(1.0)  # DELAY SOLICITADO: 1 segundo após coletar loot
                return True
    
    print(f"[LOOT] ❌ Nenhum loot detectado")
    return False

def check_and_collect_loot_SMART(ser, loot_images):
    """
    Versão INTELIGENTE da coleta de loot - Evita cliques duplicados
    Detecta círculos únicos e clica apenas UMA VEZ em cada corpo
    Usa distância mínima para evitar duplicatas
    """
    print(f"[LOOT] 🧠 SMART MODE - Coleta inteligente (sem duplicatas)")
    print(f"[LOOT] ⏳ Aguardando loot aparecer (0.8s)...")
    time.sleep(0.8)
    
    # Lista para armazenar posições únicas já detectadas
    unique_positions = []
    MIN_DISTANCE = 50  # Distância mínima entre loots (pixels)
    
    print(f"[LOOT] 🔍 Detectando círculos únicos...")
    
    # Verifica todas as imagens de loot (3 variações do círculo)
    for loot_name, loot_image in loot_images.items():
        # Busca todas as ocorrências desta imagem
        try:
            # Encontra TODAS as ocorrências na tela
            locations = list(pg.locateAllOnScreen(loot_image, confidence=0.60))
            
            for box in locations:
                center_x = int(box.left + box.width / 2)
                center_y = int(box.top + box.height / 2)
                new_pos = (center_x, center_y)
                
                # Verifica se esta posição é única (não muito próxima de outras)
                is_unique = True
                for existing_pos in unique_positions:
                    distance = ((new_pos[0] - existing_pos[0])**2 + (new_pos[1] - existing_pos[1])**2)**0.5
                    if distance < MIN_DISTANCE:
                        is_unique = False
                        break
                
                # Se é única, adiciona à lista
                if is_unique:
                    unique_positions.append(new_pos)
                    print(f"[LOOT] 📍 Círculo único detectado: {loot_name.upper()} em {new_pos}")
                    
        except Exception as e:
            # Se falhar, usa método original como fallback
            pos = find_image_ULTRA_FAST(loot_image, confidence=0.60)
            if pos and pos not in unique_positions:
                unique_positions.append(pos)
                print(f"[LOOT] 📍 Fallback: {loot_name.upper()} em {pos}")
    
    # Agora coleta cada posição única apenas UMA VEZ
    if unique_positions:
        print(f"[LOOT] 🎯 {len(unique_positions)} corpo(s) único(s) com círculo detectado(s)")
        total_collected = 0
        
        for i, pos in enumerate(unique_positions, 1):
            print(f"[LOOT] 🎯 Corpo #{i} em {pos}...")
            if click_at_position(ser, pos[0], pos[1], right_click=True):
                print(f"[LOOT] ✅ Corpo #{i} coletado!")
                total_collected += 1
                time.sleep(0.15)  # Pausa entre coletas
        
        print(f"[LOOT] 🧠 SMART: {total_collected} corpo(s) coletado(s) - Zero duplicatas!")
        return True
    else:
        print(f"[LOOT] 🧠 SMART: Nenhum círculo detectado")
        return False

def check_and_collect_loot_PROTECTED(ser, loot_images):
    """
    Versão PROTEGIDA da coleta de loot - NÃO PODE SER INTERROMPIDA
    Sistema de 3 VARREDURAS com tempo total dedicado apenas ao loot
    Durante este processo, ignora COMPLETAMENTE a detecção de inimigos
    Retorna True se coletou loot
    """
    print(f"[LOOT] 🛡️ MODO PROTEÇÃO ATIVADO - Ignorando inimigos durante coleta")
    print(f"[LOOT] ⏳ Aguardando loot aparecer (1.2s)...")
    time.sleep(1.2)  # TEMPO EXTRA para garantir que loot apareceu
    
    total_collected = 0
    
    # VARREDURA 1 - Confiança normal (0.65)
    print(f"[LOOT] 🔍 [1/3] Primeira varredura (confidence 0.65)...")
    loots_found = []
    for loot_name, loot_image in loot_images.items():
        pos = find_image_quick(loot_image, confidence=0.65)
        if pos:
            loots_found.append((loot_name, pos))
    
    # Coleta encontrados na varredura 1
    if loots_found:
        print(f"[LOOT] 💎 Varredura 1: {len(loots_found)} loot(s) encontrado(s)!")
        for loot_name, pos in loots_found:
            print(f"[LOOT] 🎯 Coletando {loot_name.upper()} em {pos}...")
            if click_at_position(ser, pos[0], pos[1], right_click=True):
                print(f"[LOOT] ✅ {loot_name.upper()} coletado!")
                total_collected += 1
                time.sleep(0.25)  # Tempo entre coletas
    
    # VARREDURA 2 - Segunda chance (0.65)
    print(f"[LOOT] 🔄 [2/3] Segunda varredura em 0.6s...")
    time.sleep(0.6)
    
    loots_found = []
    for loot_name, loot_image in loot_images.items():
        pos = find_image_quick(loot_image, confidence=0.65)
        if pos:
            loots_found.append((loot_name, pos))
    
    # Coleta encontrados na varredura 2
    if loots_found:
        print(f"[LOOT] 💎 Varredura 2: {len(loots_found)} loot(s) encontrado(s)!")
        for loot_name, pos in loots_found:
            print(f"[LOOT] 🎯 Coletando {loot_name.upper()} em {pos}...")
            if click_at_position(ser, pos[0], pos[1], right_click=True):
                print(f"[LOOT] ✅ {loot_name.upper()} coletado!")
                total_collected += 1
                time.sleep(0.25)
    
    # VARREDURA 3 - Última tentativa com confiança BAIXA (0.58)
    print(f"[LOOT] 🔄 [3/3] Varredura final (confidence BAIXA 0.58) em 0.6s...")
    time.sleep(0.6)
    
    loots_found = []
    for loot_name, loot_image in loot_images.items():
        pos = find_image_quick(loot_image, confidence=0.58)  # MUITO baixa para pegar qualquer coisa
        if pos:
            loots_found.append((loot_name, pos))
    
    # Coleta encontrados na varredura 3
    if loots_found:
        print(f"[LOOT] 💎 Varredura 3: {len(loots_found)} loot(s) encontrado(s)!")
        for loot_name, pos in loots_found:
            print(f"[LOOT] 🎯 Coletando {loot_name.upper()} em {pos}...")
            if click_at_position(ser, pos[0], pos[1], right_click=True):
                print(f"[LOOT] ✅ {loot_name.upper()} coletado!")
                total_collected += 1
                time.sleep(0.25)
    
    # Resultado final
    if total_collected > 0:
        print(f"[LOOT] 🎉 TOTAL COLETADO: {total_collected} item(s)")
        print(f"[LOOT] ⏰ Pausa final de 0.5s antes de continuar...")
        time.sleep(0.5)
        print(f"[LOOT] 🛡️ PROTEÇÃO DESATIVADA - Voltando ao combate normal")
        return True
    else:
        print(f"[LOOT] ❌ Nenhum loot coletado após 3 varreduras PROTEGIDAS")
        print(f"[LOOT] 🛡️ PROTEÇÃO DESATIVADA - Voltando ao combate normal")
        return False

def witch_combat_special(ser):
    """Combate especial contra witch - apenas 2 pressões da tecla 2 com 2s"""
    print("[INSTANT] 🧙‍♀️ Witch combat - 2x tecla 2...")
    press_key_2(ser)
    time.sleep(2.0)  # 2 segundos
    press_key_2(ser)
    time.sleep(2.0)  # 2 segundos
    print("[INSTANT] ✅ Witch combat completo!")

def normal_combat(ser):
    """Combate normal - apenas aguarda"""
    print("[INSTANT] ⚔️ Normal combat...")
    time.sleep(7.0)  # Tempo padrão de combate

def combat_loop_INSTANT(ser, enemy_images, loot_images, battle_images):
    """SISTEMA SIMPLIFICADO - usa o novo sistema independente"""
    combat_count = 0
    
    while combat_count < 10:  # Máximo de 10 combates por área
        if combat_system_independent(ser, enemy_images, loot_images, battle_images):
            combat_count += 1
        else:
            break  # Nenhum enemy encontrado
    
    print(f"[FAST] ✅ {combat_count} combates concluídos")
    return combat_count

# Função para usar em navegação
def navigate_combat_loop(ser, enemy_images, loot_images, battle_images):
    """Usa o combat loop instant para navegação"""
    return combat_loop_INSTANT(ser, enemy_images, loot_images, battle_images)

def combat_loop_ULTRA_FAST(ser, enemy_images, loot_images, battle_images):
    """
    SISTEMA SIMPLIFICADO - usa o novo sistema independente
    """
    return combat_loop_INSTANT(ser, enemy_images, loot_images, battle_images)

def combat_loop(ser, enemy_images, loot_images, battle_images):
    """
    Loop de combate inteligente com prioridades + DETECÇÃO VISUAL
    Clica com BOTÃO ESQUERDO nos inimigos
    SEMPRE coleta loot antes de procurar próximo inimigo
    NOVO: Detecta fim de batalha por borda vermelha
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
                
                # NOVO: Move mouse para centro após atacar inimigo
                print(f"[COMBAT] 🎯 Centralizando mouse após ataque...")
                move_to_screen_center(ser)
                time.sleep(0.1)  # Breve pausa
                
                # COMBATE ESPECIAL CONTRA WITCH - Pressiona tecla 2 a cada 2.2s
                if enemy_name.lower() == "witch":
                    print(f"[COMBAT] ⚡ WITCH DETECTADA! Usando combate especial com tecla 2 a cada 2.2s")
                    
                    # Divide o tempo de combate em intervalos de 2.2s
                    remaining_time = COMBAT_DELAY
                    interval = 2.2
                    
                    while remaining_time > 0:
                        # Pressiona tecla 2
                        press_key_2(ser)
                        
                        # Aguarda 2.2s ou o tempo restante (o que for menor)
                        sleep_time = min(interval, remaining_time)
                        if sleep_time > 0:
                            print(f"[COMBAT] Aguardando {sleep_time:.1f}s...")
                            time.sleep(sleep_time)
                        
                        remaining_time -= interval
                    
                    print(f"[COMBAT] ⚡ Combate especial contra WITCH concluído!")
                else:
                    # NOVA DETECÇÃO VISUAL para outros inimigos! (combat_loop normal)
                    print(f"[COMBAT] 🔍 Usando detecção VISUAL para {enemy_name}")  
                    wait_for_battle_end(ser, enemy_name.lower(), battle_images)
                
                # Pressiona 9 UMA VEZ após matar (otimizado)
                print(f"[COMBAT] Pressionando tecla 9 (1x) após matar {enemy_name}")
                press_bracket(ser)
                time.sleep(0.1)  # Pausa mínima
                
                # COLETA SINGLE de loot - Apenas 1 clique por batalha
                loot_collected = check_and_collect_loot_SINGLE(ser, loot_images)
                
                if not loot_collected:
                    # Se não teve loot, continua imediatamente
                    print(f"[COMBAT] Sem loot - Procurando próximo inimigo...")
                    time.sleep(0.05)  # Delay MÍNIMO
                
                # Continua para próximo inimigo
                continue
                
        else:
            consecutive_no_enemies += 1
            print(f"[COMBAT] Nenhum inimigo detectado ({consecutive_no_enemies}/2)")
            
            if consecutive_no_enemies >= 2:
                print(f"[COMBAT] Área limpa! Total de combates: {combat_count}")
                return combat_count
            
            time.sleep(0.5)  # REDUZIDO de 1.0s para 0.5s

# ===========================
# SISTEMA DE NAVEGAÇÃO COM INTERRUPÇÃO
# ===========================

def navigate_to_flag(ser, flag_name, flag_image, delay_after, enemy_images, loot_images, battle_images):
    """
    Navega para uma flag com sistema de interrupção por inimigos
    Se interrompido, retoma a navegação
    Flag 'subida1' usa clique DIREITO, outras usam ESQUERDO
    NOVO: Suporte para detecção visual de batalha
    """
    action_completed = False
    attempt_count = 0
    
    while not action_completed and attempt_count < 5:
        attempt_count += 1
        print(f"\n[NAV] Navegando para {flag_name} (tentativa {attempt_count}/5)...")
        
        # NOVA DETECÇÃO GLOBAL: Verifica inimigos INSTANTANEAMENTE durante navegação
        if check_for_immediate_combat(ser, enemy_images, loot_images, battle_images):
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
        
        # SUBIDA1 usa clique DIREITO, outras flags usam ESQUERDO
        use_right_click = (flag_name.lower() == "subida1")
        click_type = "DIREITO" if use_right_click else "ESQUERDO"
        
        if use_right_click:
            print(f"[NAV] ⚠️ FLAG ESPECIAL: {flag_name} detectada - Usando CLIQUE DIREITO!")
            print(f"[NAV] 🔄 CONFIRMAÇÃO: subida1.png = CLIQUE DIREITO GARANTIDO!")
        
        # Clica na flag
        if click_at_position(ser, pos[0], pos[1], right_click=use_right_click):
            print(f"[NAV] ✅ Clique {click_type} em {flag_name} bem-sucedido!")
            
            # Move mouse para centro da tela
            move_to_screen_center(ser)
            time.sleep(0.1)
            
            # Delay após clicar na flag COM MONITORAMENTO (reduzido em 45%)
            if delay_after > 0:
                reduced_delay = delay_after * 0.55  # 45% de redução
                print(f"[NAV] Aguardando {reduced_delay:.1f}s após {flag_name} (reduzido 45%, com monitoramento)...")
                was_interrupted = monitored_delay(ser, reduced_delay, flag_name, enemy_images, loot_images, battle_images)
                
                if was_interrupted:
                    print(f"[NAV] *** DELAY INTERROMPIDO! RETOMANDO {flag_name} ***")
                    continue  # Retoma do início desta flag
            
            action_completed = True
        else:
            print(f"[NAV] Falha ao clicar em {flag_name}")
            time.sleep(1.0)
    
    return action_completed

def monitored_delay(ser, seconds, context, enemy_images, loot_images, battle_images):
    """
    Delay ULTRA OTIMIZADO com verificação instantânea
    """
    start_time = time.time()
    end_time = start_time + seconds
    check_interval = 0.05  # EXTREMAMENTE RÁPIDO - 50ms
    
    while time.time() < end_time:
        # Verificação INSTANTÂNEA de inimigos
        if check_for_immediate_combat(ser, enemy_images, loot_images, battle_images):
            return True  # Interrompido por combate
        
        # Pausa mínima
        time.sleep(check_interval)
    
    return False  # Delay completo

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
    
    # Carrega imagens de batalha (bordas vermelhas)
    battle_images = {
        "battle_witch": os.path.abspath(os.path.join("..", "enemy", "battle_witch.png")),
        "battle_valkyrie": os.path.abspath(os.path.join("..", "enemy", "battle_valkyrie.png")),
        "battle_amazon": os.path.abspath(os.path.join("..", "enemy", "battle_amazon.png")),
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
    
    print("\n[DEBUG] Verificando imagens de batalha...")
    for name, path in battle_images.items():
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
                navigate_to_flag(ser, flag_name, flag_image, delay_after, enemy_images, loot_images, battle_images)
            
            print("\n[PHASE] ✅ Parte superior completada!")
            
            # ========== SUBTERRÂNEO ==========
            print("\n[PHASE] SUBTERRÂNEO - ROTA COMPLETA")
            for flag_name, delay_after in UNDERGROUND_ROUTE:
                flag_image = os.path.abspath(os.path.join("..", "flags", "amazon_camp", f"{flag_name}.png"))
                navigate_to_flag(ser, flag_name, flag_image, delay_after, enemy_images, loot_images, battle_images)
            
            print("\n[PHASE] ✅ Subterrâneo completado!")
            
            # ========== VOLTA PARA FLAG 1 ==========
            print("\n[PHASE] VOLTANDO PARA FLAG 1...")
            flag1_image = os.path.abspath(os.path.join("..", "flags", "amazon_camp", "am_a1.png"))
            navigate_to_flag(ser, "am_a1", flag1_image, 10, enemy_images, loot_images, battle_images)
            
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
    print("- ⚡ WITCH: Tecla 2 a cada 2.2s durante combate (ESPECIAL)")
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
