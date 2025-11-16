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
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False
    print("[AVISO] pytesseract não disponível. Usando detecção por cores.")

# Configurações
COM_PORT = "COM11"
BAUD_RATE = 9600
DETECT_CONFIDENCE = 0.8

# Thresholds de HP (baseados nos templates criados)
MAX_HP = 1755
EMERGENCY_HP = 800
CRITICAL_HP = 1000  
LOW_HP = 1400
SAFE_HP = 1600

# Hotkeys de healing
EMERGENCY_KEY = "F1"
CRITICAL_KEY = "3"
LOW_KEY = "2"
MANA_KEY = "F4"

# Delays
CHECK_INTERVAL = 0.5
HEALING_COOLDOWN = 1.0

# ==========================================
# Configuração PyAutoGUI
# ==========================================
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.01

# ==========================================
# Desativar Aceleração do Mouse
# ==========================================
def disable_mouse_acceleration():
    """Desativa a aceleração do mouse no Windows"""
    try:
        # Definir SPI_SETMOUSE para desativar aceleração
        SPI_SETMOUSE = 0x0004
        
        # Parâmetros: [acceleration, threshold1, threshold2]
        # [0, 0, 0] = sem aceleração
        mouse_params = (ctypes.c_int * 3)(0, 0, 0)
        
        result = ctypes.windll.user32.SystemParametersInfoW(
            SPI_SETMOUSE,
            0,
            mouse_params,
            0
        )
        
        if result:
            print("[MOUSE] Aceleração desativada!")
        else:
            print("[AVISO] Não foi possível desativar a aceleração do mouse")
            
    except Exception as e:
        print(f"[AVISO] Erro ao configurar mouse: {e}")

# ==========================================
# Comunicação Serial
# ==========================================
def send_arduino_command(ser, command):
    """Envia comando para Arduino e aguarda confirmação"""
    try:
        ser.write(f"{command}\n".encode())
        ser.flush()
        
        # Aguardar resposta (timeout de 1 segundo)
        start_time = time.time()
        while time.time() - start_time < 1.0:
            if ser.in_waiting > 0:
                response = ser.readline().decode().strip()
                if response:
                    print(f"[ARDUINO] {response}")
                    return True
            time.sleep(0.01)
        
        print(f"[AVISO] Arduino não respondeu ao comando: {command}")
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
        hp_bar_region = (16, 9, 700, 16)
        
        screenshot = pyautogui.screenshot(region=hp_bar_region)
        width, height = screenshot.size
        total_pixels = width * height
        colored_pixels = 0
        
        # Analisa cores da barra de HP
        for x in range(width):
            for y in range(height):
                r, g, b = screenshot.getpixel((x, y))
                
                # Detecta pixels coloridos da barra
                if (r > 50 or g > 50) and (r + g + b) > 150:
                    colored_pixels += 1
        
        # Calcula percentual baseado na proporção de pixels coloridos
        if total_pixels > 0:
            hp_percentage = (colored_pixels / total_pixels) * 100
            hp_percentage = min(hp_percentage * 1.2, 100)
            return round(hp_percentage)
        
        return -1
        
    except Exception as e:
        print(f"[ERRO] Detecção de HP por percentual: {e}")
        return -1

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
                        print("NAO CLASSIFICADO")
        
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
            ("../healings/hpcheio.png", 1755),      # HP cheio
            ("../healings/hp80p.png", 1400),        # HP ~80%  
            ("../healings/hpmedio.png", 1000),      # HP médio
        ]
        
        # Tenta cada template com diferentes níveis de confiança
        for template_path, hp_value in templates:
            if os.path.exists(template_path):
                for confidence in [0.9, 0.8, 0.7, 0.6]:
                    try:
                        result = pyautogui.locateOnScreen(template_path, 
                                                        confidence=confidence,
                                                        region=hp_bar_region)
                        if result:
                            template_name = os.path.basename(template_path)
                            print(f"[TEMPLATE] {template_name} encontrado (conf: {confidence})")
                            return hp_value
                    except Exception:
                        continue
        
        print("[DEBUG] Nenhum template encontrado")
        return -1
        
    except Exception as e:
        print(f"[ERRO] Template matching: {e}")
        return -1

def get_hp_by_bar_analysis():
    """
    Método de fallback que analisa a largura da barra de HP
    """
    try:
        # Use uma região mais ampla para detectar mudanças na barra
        hp_bar_region = (16, 9, 400, 10)
        screenshot = pyautogui.screenshot(region=hp_bar_region)
        
        # Analisa linha por linha para encontrar a barra
        width, height = screenshot.size
        max_green_width = 0
        
        for y in range(height):
            green_width = 0
            for x in range(width):
                r, g, b = screenshot.getpixel((x, y))
                
                # Detecta se é uma cor relacionada à barra de HP
                if g > 80 and (g > r) and (g > b):  # Verde predominante
                    green_width = x
                elif r > 100 and g > 80 and b < 80:  # Amarelo/Laranja
                    green_width = x
                elif r > 100 and g < 80 and b < 80:  # Vermelho
                    green_width = x
                    
            max_green_width = max(max_green_width, green_width)
        
        if max_green_width > 0:
            # Estima HP baseado na largura da barra
            hp_percentage = (max_green_width / width) * 100
            estimated_hp = int((hp_percentage / 100) * MAX_HP)
            return estimated_hp
            
        return -1
        
    except Exception as e:
        print(f"[ERRO] Análise da barra: {e}")
        return -1

def get_hp_by_color():
    """Fallback: detecção simples por cor predominante"""
    try:
        hp_percentage = get_hp_percentage()
        if hp_percentage > 0:
            return int((hp_percentage / 100) * MAX_HP)
        return -1
    except Exception as e:
        print(f"[ERRO] Detecção por cor: {e}")
        return get_hp_percentage()

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
    print("[CONFIG] Vermelho = HP baixo - ' + tecla 3")
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
    
    try:
        # Conectar com Arduino
        print(f"[SERIAL] Conectando {COM_PORT} @ {BAUD_RATE}...")
        ser = serial.Serial(COM_PORT, BAUD_RATE, timeout=1)
        time.sleep(2)  # Aguardar inicialização do Arduino
        
        print(f"[OK] Conectado em {COM_PORT}")
        
        # Aguardar Arduino estar pronto
        print("[SERIAL] Aguardando Arduino...")
        ready_received = False
        start_time = time.time()
        
        while time.time() - start_time < 5:  # Timeout de 5 segundos
            if ser.in_waiting > 0:
                try:
                    response = ser.readline().decode().strip()
                    if response:
                        print(f"[ARDUINO] {response}")
                        if "READY" in response:
                            ready_received = True
                            break
                except UnicodeDecodeError:
                    pass  # Ignora caracteres inválidos
            time.sleep(0.1)
        
        if not ready_received:
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