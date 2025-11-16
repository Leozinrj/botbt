#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pyautogui
import serial
import time
import threading
import sys
import os
import ctypes
from ctypes import wintypes
import cv2
import numpy as np
try:
    import pytesseract
    # Configure tesseract path if needed (adjust path as necessary)
    # pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    print("[AVISO] pytesseract não disponível. Usando detecção por cores.")

# Configurações
COM_PORT = "COM11"  # Porta do Arduino
BAUD_RATE = 9600
DETECT_CONFIDENCE = 0.8

# Thresholds de HP (baseados nos templates criados)
MAX_HP = 1755           # HP máximo do personagem
EMERGENCY_HP = 800      # HP crítico - healing urgente (F1)
CRITICAL_HP = 1000      # HP médio - usar tecla 3 (hpmedio.png)  
LOW_HP = 1400           # HP 80% - usar tecla 2 (hp80p.png)
SAFE_HP = 1600          # HP alto - sem healing (próximo do cheio)

# Hotkeys de healing - usando números ao invés de F-keys
EMERGENCY_KEY = "F1"    # F1 ainda para emergência
CRITICAL_KEY = "3"      # Tecla 3 quando HP ≤ 50%
LOW_KEY = "2"           # Tecla 2 quando HP ≤ 70%
MANA_KEY = "F4"         # Mana Potion

# Delays
CHECK_INTERVAL = 0.5    # Intervalo entre checagens de HP (segundos)
HEALING_COOLDOWN = 1.0  # Cooldown após usar healing (segundos)

# ==========================================
# Configuração PyAutoGUI
# ==========================================
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.01

# ==========================================
# Desabilitar aceleração do mouse (Windows)
# ==========================================
def disable_mouse_acceleration():
    """Desabilita a aceleração do mouse no Windows para precisão máxima"""
    try:
        # Definir parâmetros do mouse para precisão
        SPI_SETMOUSE = 0x0004
        SPI_GETMOUSE = 0x0003
        
        # Obter configuração atual
        mouse_params = (ctypes.c_int * 3)()
        ctypes.windll.user32.SystemParametersInfoW(SPI_GETMOUSE, 0, mouse_params, 0)
        
        # Desabilitar aceleração: [0, 0, 0]
        mouse_params[0] = 0  # Sem aceleração
        mouse_params[1] = 0  # Sem aceleração
        mouse_params[2] = 0  # Limiar de aceleração
        
        # Aplicar configuração
        result = ctypes.windll.user32.SystemParametersInfoW(SPI_SETMOUSE, 0, mouse_params, 0)
        
        if result:
            print("[MOUSE] Aceleração desativada!")
        else:
            print("[AVISO] Não foi possível desativar a aceleração do mouse")
            
    except Exception as e:
        print(f"[ERRO] Configuração do mouse: {e}")

# ==========================================
# Comunicação com Arduino
# ==========================================
def send_arduino_command(ser, command, timeout=2.0):
    """Envia comando para Arduino e aguarda resposta OK"""
    try:
        ser.write(f"{command}\n".encode())
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if ser.in_waiting > 0:
                response = ser.readline().decode().strip()
                if response == "OK":
                    return True
                elif response.startswith("ERR"):
                    print(f"[ERRO] Arduino: {response}")
                    return False
        
        print(f"[ERRO] Timeout no comando: {command}")
        return False
        
    except Exception as e:
        print(f"[ERRO] Comunicação serial: {e}")
        return False

def arduino_key(ser, key):
    """Envia comando de tecla especial para Arduino"""
    return send_arduino_command(ser, f"KE {key}")

# ==========================================
# Detecção de HP
# ==========================================
def get_hp_percentage():
    """
    Detecta o percentual atual de HP analisando a barra de vida.
    Retorna valor entre 0-100 ou -1 se erro.
    """
    try:
        # Coordenadas da barra de HP baseadas na sua interface
        # HP fica no topo esquerdo da tela
        hp_bar_region = (16, 9, 700, 16)  # x, y, width, height
        
        # Captura a região da barra de HP
        screenshot = pyautogui.screenshot(region=hp_bar_region)
        
        # Converte para análise de pixels
        width, height = screenshot.size
        total_pixels = width * height
        colored_pixels = 0
        
        # Analisa cores da barra de HP
        for x in range(width):
            for y in range(height):
                r, g, b = screenshot.getpixel((x, y))
                
                # Detecta pixels coloridos da barra (verde, amarelo, vermelho)
                # Verde (HP alto): G > R e G > B
                # Amarelo (HP médio): R ≈ G > B  
                # Vermelho (HP baixo): R > G e R > B
                if (r > 50 or g > 50) and (r + g + b) > 150:
                    # Pixel pertence à barra de HP
                    colored_pixels += 1
        
        # Calcula percentual baseado na proporção de pixels coloridos
        if total_pixels > 0:
            hp_percentage = (colored_pixels / total_pixels) * 100
            # Ajuste para valores mais realistas (a barra não ocupa 100% da região)
            hp_percentage = min(hp_percentage * 1.2, 100)
            return round(hp_percentage)
        
        return -1
        
    except Exception as e:
        print(f"[ERRO] Detecção de HP: {e}")
        return -1

def get_hp_by_color_detection():
    """
    Detecta HP analisando as cores específicas da barra.
    Verde escuro = HP cheio
    Verde musgo = HP 80% 
    Amarelo = HP médio
    Vermelho = HP baixo
    """
    try:
        # Região da barra de HP
        hp_bar_region = (9, 7, 497, 7)
        
        screenshot = pyautogui.screenshot(region=hp_bar_region)
        width, height = screenshot.size
        
        # Salva debug da região capturada
        screenshot.save("../debug_hp_region.png")
        
        # Contadores para cada tipo de cor
        dark_green_pixels = 0    # HP cheio (verde escuro)
        light_green_pixels = 0   # HP 80% (verde musgo)  
        yellow_pixels = 0        # HP médio (amarelo)
        red_pixels = 0          # HP baixo (vermelho)
        total_colored = 0
        
        # Analisa cada pixel da barra
        for x in range(width):
            for y in range(height):
                r, g, b = screenshot.getpixel((x, y))
                
                # Ignora pixels muito escuros (fundo) - mais permissivo
                brightness = r + g + b
                if brightness < 50:  # Reduzido de 80 para 50
                    continue
                    
                total_colored += 1
                
                # Classificação das cores - critérios melhorados
                if g > 80 and r < 120 and b < 120 and g > r:
                    # Verde (escuro ou musgo)
                    if g > 130:
                        dark_green_pixels += 1  # Verde mais intenso = HP cheio
                    else:
                        light_green_pixels += 1  # Verde menos intenso = HP 80%
                elif r > 100 and g > 80 and b < 100 and r > b:
                    # Amarelo - HP médio
                    yellow_pixels += 1
                elif r > 80 and g < 80 and b < 80 and r > g and r > b:
                    # Vermelho - HP baixo (critérios mais sensíveis)
                    red_pixels += 1
                
                # Debug para alguns pixels - só mostra os primeiros 5 para não spam
                if total_colored <= 5:
                    print(f"[PIXEL DEBUG] x={x}, y={y}: RGB({r},{g},{b}) -> ", end="")
                    if g > 80 and r < 120 and b < 120 and g > r:
                        if g > 130:
                            print("VERDE ESCURO")
                        else:
                            print("VERDE MUSGO")
                    elif r > 100 and g > 80 and b < 100 and r > b:
                        print("AMARELO")
                    elif r > 80 and g < 80 and b < 80 and r > g and r > b:
                        print("VERMELHO")
                    else:
                        print("NÃO CLASSIFICADO")
        
        print(f"[DEBUG] Região: {hp_bar_region}, Tamanho: {width}x{height}")
        print(f"[DEBUG] Total pixels coloridos: {total_colored}")
        
        if total_colored == 0:
            print("[DEBUG] Nenhum pixel colorido encontrado na região")
            return "unknown"
        
        # Calcula proporções
        total = dark_green_pixels + light_green_pixels + yellow_pixels + red_pixels
        if total == 0:
            print("[DEBUG] Nenhum pixel classificado nas cores esperadas")
            return "unknown"
            
        dark_green_ratio = dark_green_pixels / total
        light_green_ratio = light_green_pixels / total  
        yellow_ratio = yellow_pixels / total
        red_ratio = red_pixels / total
        
        print(f"[DEBUG] Cores detectadas:")
        print(f"  Verde escuro: {dark_green_pixels} ({dark_green_ratio:.2%})")
        print(f"  Verde musgo: {light_green_pixels} ({light_green_ratio:.2%})")
        print(f"  Amarelo: {yellow_pixels} ({yellow_ratio:.2%})")
        print(f"  Vermelho: {red_pixels} ({red_ratio:.2%})")
        
        # Determina estado do HP baseado na cor predominante - prioridade para vermelho
        if red_ratio > 0.05:  # Prioridade para vermelho - threshold muito baixo
            return "low"    # HP baixo - vermelho
        elif dark_green_ratio > 0.4:
            return "full"  # HP cheio - verde escuro
        elif light_green_ratio > 0.2:
            return "80p"   # HP 80% - verde musgo
        elif yellow_ratio > 0.2:
            return "medium" # HP médio - amarelo
        else:
            print(f"[DEBUG] Nenhuma cor atingiu threshold mínimo")
            print(f"[DEBUG] Ratios: R={red_ratio:.3f}, VE={dark_green_ratio:.3f}, VM={light_green_ratio:.3f}, A={yellow_ratio:.3f}")
            return "unknown"
            
    except Exception as e:
        print(f"[ERRO] Detecção de cores: {e}")
        return "unknown"

def get_hp_by_simple_template():
    """
    Método mais simples usando apenas comparação de similaridade
    """
    try:
        # Região da barra de HP
        hp_bar_region = (9, 7, 497, 7)
        current_screenshot = pyautogui.screenshot(region=hp_bar_region)
        
        # Salva screenshot atual para debug
        current_screenshot.save("../healings/current_hp.png")
        
        # Templates com seus valores de HP correspondentes
        templates = [
            ("../healings/hpcheio.png", 1755, "CHEIO"),
            ("../healings/hp80p.png", 1400, "80%"),
            ("../healings/hpmedio.png", 1000, "MÉDIO"),
        ]
        
        for template_path, hp_value, description in templates:
            if os.path.exists(template_path):
                try:
                    # Tenta encontrar o template na tela
                    location = pyautogui.locateOnScreen(template_path, 
                                                      confidence=0.8,
                                                      region=hp_bar_region)
                    if location:
                        print(f"[TEMPLATE] {description} detectado - HP: {hp_value}")
                        return hp_value
                        
                except pyautogui.ImageNotFoundException:
                    continue
                except Exception as e:
                    print(f"[DEBUG] Erro template {description}: {e}")
                    continue
        
        print("[DEBUG] Nenhum template encontrado")
        return -1
        
    except Exception as e:
        print(f"[ERRO] Template simples: {e}")
        return -1

def get_hp_by_bar_analysis():
    """
    Detecta HP analisando o comprimento da barra verde.
    Retorna valor absoluto aproximado baseado no HP máximo.
    """
    try:
        # Região da barra de HP (só a parte colorida)
        hp_bar_region = (16, 9, 700, 16)
        
        screenshot = pyautogui.screenshot(region=hp_bar_region)
        width, height = screenshot.size
        
        # Encontra onde a barra verde termina (vai da esquerda para direita)
        green_end = 0
        
        for x in range(width):
            has_green_in_column = False
            for y in range(height):
                r, g, b = screenshot.getpixel((x, y))
                
                # Detecta pixel verde da barra de HP
                if g > 100 and g > r and g > b:
                    has_green_in_column = True
                    break
            
            if has_green_in_column:
                green_end = x
            else:
                # Se não tem mais verde, a barra acabou
                break
        
        # Calcula HP baseado na proporção da barra preenchida
        if width > 0:
            fill_ratio = green_end / width
            estimated_hp = int(MAX_HP * fill_ratio)
            
            # Garante valores mínimos realistas
            if estimated_hp < 100 and fill_ratio > 0.1:
                estimated_hp = max(estimated_hp, 200)
            
            return estimated_hp
        
        return -1
            
    except Exception as e:
        print(f"[ERRO] Análise da barra: {e}")
        return -1

def get_hp_by_color_analysis():
    """
    Método fallback: analisa cores da barra de HP 
    Retorna percentual (0-100)
    """
    try:
        hp_bar_region = (16, 9, 700, 16)
        screenshot = pyautogui.screenshot(region=hp_bar_region)
        width, height = screenshot.size
        total_pixels = width * height
        
        bar_pixels = 0
        for x in range(width):
            for y in range(height):
                r, g, b = screenshot.getpixel((x, y))
                brightness = r + g + b
                if brightness > 80:
                    bar_pixels += 1
        
        if total_pixels > 0:
            fill_ratio = bar_pixels / total_pixels
            if fill_ratio > 0.9:
                return 95
            elif fill_ratio > 0.7:
                return 80
            elif fill_ratio > 0.5:
                return 60
            elif fill_ratio > 0.3:
                return 40
            else:
                return 20
        return -1
            
    except Exception as e:
        print(f"[ERRO] Análise de cor: {e}")
        return -1
    """
    Método mais preciso: analisa o preenchimento da barra de HP.
    Baseado na proporção de pixels coloridos vs fundo escuro
    """
    try:
        # Região da barra de HP (definida manualmente com configurador)
        hp_bar_region = (9, 7, 497, 7)
        
        screenshot = pyautogui.screenshot(region=hp_bar_region)
        width, height = screenshot.size
        total_pixels = width * height
        
        # Conta pixels que pertencem à barra (método mais simples e preciso)
        last_colored_x = 0
        
        for x in range(width):
            has_color_in_column = False
            for y in range(height):
                r, g, b = screenshot.getpixel((x, y))
                
                # Detecta qualquer pixel colorido da barra
                brightness = r + g + b
                if brightness > 80:
                    has_color_in_column = True
                    break
            
            if has_color_in_column:
                last_colored_x = x
        
        # Calcula HP baseado no comprimento da barra preenchida
        if width > 0:
            fill_ratio = (last_colored_x + 1) / width
            estimated_hp = int(MAX_HP * fill_ratio)
            
            print(f"[DEBUG] Barra: {width}px, Preenchida: {last_colored_x + 1}px ({fill_ratio:.1%})")
            print(f"[DEBUG] HP estimado: {estimated_hp}/{MAX_HP}")
            
            return estimated_hp
        
        return -1
            
    except Exception as e:
        print(f"[ERRO] Análise de cor: {e}")
        return -1
    """
    Método alternativo: detecta HP usando templates de barras.
    Procura por imagens de referência da barra em diferentes estados.
    """
    try:
        # Lista de templates ordenados por prioridade (do mais baixo ao mais alto)
        hp_templates = [
            ("../healings/hp_emergency.png", 10),  # HP crítico ~10%
            ("../healings/hp_critical.png", 25),   # HP baixo ~25%
            ("../healings/hp_low.png", 45),        # HP médio ~45%
            ("../healings/hp_medium.png", 65),     # HP médio-alto ~65%
            ("../healings/hp_high.png", 85),       # HP alto ~85%
            ("../healings/hp_full.png", 100),      # HP cheio ~100%
        ]
        
        for template_path, hp_value in hp_templates:
            if os.path.exists(template_path):
                try:
                    result = pyautogui.locateOnScreen(template_path, confidence=DETECT_CONFIDENCE)
                    if result:
                        return hp_value
                except:
                    continue
        
        # Se não encontrou nenhum template, usa método de cores
        return get_hp_percentage()
        
    except Exception as e:
        print(f"[ERRO] Detecção por template: {e}")
        return get_hp_percentage()

def get_current_hp():
    """
    Detecta o HP atual usando detecção por cores.
    Retorna o estado do HP como string.
    """
    try:
        # Método principal: detecção por cores
        hp_state = get_hp_by_color_detection()
        
        if hp_state != "unknown":
            state_map = {
                "full": "HP Cheio (Verde escuro)",
                "80p": "HP 80% (Verde musgo)", 
                "medium": "HP Médio (Amarelo)",
                "low": "HP Baixo (Vermelho)"
            }
            print(f"[HP] {state_map.get(hp_state, hp_state)}")
            return hp_state
        
        # Se detecção de cores falhou, retorna unknown
        print("[DEBUG] Detecção por cores não conseguiu identificar o estado")
        return "unknown"
        
    except Exception as e:
        print(f"[ERRO] get_current_hp: {e}")
        return "unknown"

# ==========================================
# Sistema de Healing
# ==========================================
def execute_healing(ser, hp_state):
    """
    Executa o healing apropriado baseado no estado do HP detectado por cores.
    hp_state: 'full', '80p', 'medium', 'low' ou 'unknown'
    Retorna True se executou healing, False caso contrário.
    """
    try:
        healing_used = False
        
        if hp_state == "full":
            # HP cheio (verde escuro) - não faz nada
            print("[HP] HP cheio (verde escuro) - sem necessidade de healing")
            return False
            
        elif hp_state == "80p":
            # HP 80% (verde musgo) - aperta 2
            print("[HEALING] HP 80% (verde musgo) - usando tecla 2")
            if arduino_key(ser, "2"):
                healing_used = True
                
        elif hp_state == "medium":
            # HP médio (amarelo) - aperta 3
            print("[HEALING] HP médio (amarelo) - usando tecla 3")
            if arduino_key(ser, "3"):
                healing_used = True
                
        elif hp_state == "low":
            # HP baixo (vermelho) - aperta apostrofe (') + tecla 3
            print("[EMERGENCY] HP baixo (vermelho) - usando ' + tecla 3")
            if arduino_key(ser, "'"):
                print("[DEBUG] Apostrofe (') enviado, aguardando 0.2s...")
                time.sleep(0.2)
                if arduino_key(ser, "3"):
                    healing_used = True
                    print("[DEBUG] Sequência ' + 3 completada")
                    
        elif hp_state == "unknown":
            print("[AVISO] Estado do HP desconhecido - sem healing")
            return False
        
        if healing_used:
            time.sleep(0.5)  # Pausa após healing
            return True
            
        return False
        
    except Exception as e:
        print(f"[ERRO] execute_healing: {e}")
        return False

# ==========================================
# Loop Principal de Healing
# ==========================================
def healing_loop(ser):
    """
    Loop principal de healing baseado em detecção de cores.
    """
    print("\n[HEALING] Sistema baseado em cores iniciado!")
    print("[CONFIG] Verde escuro = HP cheio - sem healing")
    print("[CONFIG] Verde musgo = HP 80% - tecla 2")
    print("[CONFIG] Amarelo = HP médio - tecla 3") 
    print("[CONFIG] Vermelho = HP baixo - F1 + tecla 3")
    print(f"[CONFIG] Intervalo: {CHECK_INTERVAL}s")
    
    try:
        # Ativar modo de execução no Arduino
        send_arduino_command(ser, "B1")
        
        last_hp_state = None
        healing_count = 0
        
        while True:
            # Detectar estado do HP por cores
            hp_state = get_current_hp()
            
            if hp_state == "unknown":
                print("[AVISO] Estado do HP desconhecido, tentando novamente...")
                time.sleep(CHECK_INTERVAL)
                continue
                
            # Só executa healing se mudou de estado ou se for crítico
            if hp_state != last_hp_state or hp_state == "low":
                if execute_healing(ser, hp_state):
                    healing_count += 1
                    print(f"[STATS] Healings executados: {healing_count}")
                
                last_hp_state = hp_state
                
            time.sleep(CHECK_INTERVAL)
            
    except KeyboardInterrupt:
        print("\n[INFO] Healing interrompido pelo usuário")
        # Desativar modo de execução 
        send_arduino_command(ser, "B0")
    except Exception as e:
        print(f"[ERRO] Loop de healing: {e}")
        send_arduino_command(ser, "B0")

# ==========================================
# Função Principal
# ==========================================
def main():
    """Função principal do sistema de healing"""
    print("=" * 50)
    print("SISTEMA DE HEALING AUTOMÁTICO")
    print("=" * 50)
    
    # Desabilitar aceleração do mouse
    disable_mouse_acceleration()
    
    # Conectar com Arduino
    print(f"\n[SERIAL] Conectando {COM_PORT} @ {BAUD_RATE}...")
    
    try:
        with serial.Serial(COM_PORT, BAUD_RATE, timeout=1) as ser:
            print(f"[OK] Conectado em {COM_PORT}")
            
            # Aguardar Arduino inicializar
            print("[SERIAL] Aguardando Arduino...")
            time.sleep(2)
            
            # Verificar comunicação
            response_received = False
            for _ in range(10):
                if ser.in_waiting > 0:
                    line = ser.readline().decode().strip()
                    if "READY" in line:
                        response_received = True
                        break
                time.sleep(0.1)
            
            if not response_received:
                print("[AVISO] Não recebeu READY, mas continuando...")
            else:
                print("[OK] Arduino pronto!")
            
            # Aguardar input do usuário
            input("\nENTER para iniciar o sistema de healing...")
            
            # Iniciar loop de healing
            healing_loop(ser)
            
    except serial.SerialException as e:
        print(f"[ERRO] Serial: {e}")
        print("Verifique:")
        print("1. Arduino conectado na porta correta")
        print("2. Drivers instalados")
        print("3. Porta não sendo usada por outro programa")
    except Exception as e:
        print(f"[ERRO] Inesperado: {e}")
    
    print("\n[FIM] Sistema encerrado.")

if __name__ == "__main__":
    main()