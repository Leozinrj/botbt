#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste dos templates de HP
"""

import pyautogui
import os

def test_hp_templates():
    """Testa os templates de HP"""
    print("=== TESTE DOS TEMPLATES DE HP ===")
    print("Posicione a janela do jogo e pressione ENTER")
    input("Pronto? ")
    
    # Região da barra de HP (mais ampla para incluir templates maiores)
    hp_bar_region = (5, 5, 510, 15)
    
    # Captura atual
    current_screenshot = pyautogui.screenshot(region=hp_bar_region)
    current_screenshot.save("../healings/current_test.png")
    print("Screenshot atual salva: ../healings/current_test.png")
    
    # Templates para testar
    templates = [
        ("../healings/hpcheio.png", 1755, "HP CHEIO"),
        ("../healings/hp80p.png", 1400, "HP 80%"),
        ("../healings/hpmedio.png", 1000, "HP MÉDIO"),
    ]
    
    print("\nTestando templates:")
    
    found_match = False
    for template_path, hp_value, description in templates:
        if os.path.exists(template_path):
            print(f"\n--- Testando {description} ---")
            print(f"Arquivo: {template_path}")
            
            try:
                # Teste com diferentes níveis de confidence
                for confidence in [0.9, 0.8, 0.7, 0.6]:
                    try:
                        result = pyautogui.locateOnScreen(template_path,
                                                        confidence=confidence,
                                                        region=hp_bar_region)
                        if result:
                            print(f"✅ MATCH encontrado com confidence {confidence}")
                            print(f"   HP detectado: {hp_value}")
                            print(f"   Ação: {get_action_for_hp(hp_value)}")
                            found_match = True
                            break
                    except pyautogui.ImageNotFoundException:
                        continue
                    except Exception as e:
                        print(f"   Erro confidence {confidence}: {e}")
                        continue
                        
                if not found_match:
                    print(f"❌ Nenhum match encontrado para {description}")
                    
            except Exception as e:
                print(f"   Erro geral: {e}")
        else:
            print(f"❌ Arquivo não encontrado: {template_path}")
    
    if not found_match:
        print("\n⚠️  NENHUM TEMPLATE ENCONTRADO!")
        print("Possíveis problemas:")
        print("1. As imagens não correspondem exatamente")
        print("2. A região pode estar incorreta") 
        print("3. O HP atual não corresponde a nenhum template")
        print("\nVerifique as imagens na pasta healings/")

def get_action_for_hp(hp_value):
    """Retorna a ação que seria tomada para o HP"""
    if hp_value <= 800:
        return "Usar F1 (Emergency)"
    elif hp_value <= 1000:
        return "Usar tecla 3 (Medium)"
    elif hp_value <= 1400:
        return "Usar tecla 2 (80%)"
    else:
        return "Sem healing (Full)"

if __name__ == "__main__":
    test_hp_templates()