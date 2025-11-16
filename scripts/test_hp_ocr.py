#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de teste para verificar a detecção de HP por OCR
"""

import pyautogui
import time
import cv2
import numpy as np

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
    print("[INFO] pytesseract disponível")
except ImportError:
    TESSERACT_AVAILABLE = False
    print("[AVISO] pytesseract não disponível")

def test_hp_ocr():
    """Teste de OCR para ler números da barra de HP"""
    print("=== TESTE DE OCR PARA HP ===")
    print("Posicione a janela do jogo e pressione ENTER")
    input("Pronto? ")
    
    # Diferentes regiões para testar
    regions = [
        ("HP numbers região 1", (140, 6, 250, 20)),
        ("HP numbers região 2", (175, 9, 180, 16)),
        ("HP numbers região 3", (120, 5, 300, 25)),
        ("Região ampla da barra", (16, 6, 400, 25)),
    ]
    
    for name, region in regions:
        print(f"\n--- Testando {name}: {region} ---")
        
        try:
            # Captura a região
            screenshot = pyautogui.screenshot(region=region)
            filename = f"../healings/hp_ocr_{name.replace(' ', '_').lower()}.png"
            screenshot.save(filename)
            print(f"Imagem salva: {filename}")
            
            if TESSERACT_AVAILABLE:
                # OCR básico
                text1 = pytesseract.image_to_string(screenshot).strip()
                print(f"OCR básico: '{text1}'")
                
                # OCR só números
                config = '--psm 6 -c tessedit_char_whitelist=0123456789/'
                text2 = pytesseract.image_to_string(screenshot, config=config).strip()
                print(f"OCR números: '{text2}'")
                
                # OCR linha única
                config = '--psm 7 -c tessedit_char_whitelist=0123456789/'
                text3 = pytesseract.image_to_string(screenshot, config=config).strip()
                print(f"OCR linha: '{text3}'")
                
                # Pré-processamento
                img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                _, thresh = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY)
                resized = cv2.resize(thresh, (0, 0), fx=2, fy=2)
                
                # OCR na imagem processada
                text4 = pytesseract.image_to_string(resized, config='--psm 7 -c tessedit_char_whitelist=0123456789/').strip()
                print(f"OCR processado: '{text4}'")
                
                # Tenta extrair HP
                import re
                for text in [text1, text2, text3, text4]:
                    pattern = r'(\d+)/\d+'
                    match = re.search(pattern, text)
                    if match:
                        hp = int(match.group(1))
                        print(f"*** HP DETECTADO: {hp} ***")
                        break
                else:
                    print("Nenhum HP detectado nesta região")
            else:
                print("OCR não disponível")
                
        except Exception as e:
            print(f"Erro na região {name}: {e}")
    
    print("\n=== RESUMO ===")
    print("Verifique as imagens salvas na pasta healings/")
    print("A melhor região será usada no sistema de healing")

if __name__ == "__main__":
    test_hp_ocr()