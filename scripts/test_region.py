#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste simples da região HP
"""

import pyautogui
import time

def test_region():
    print("Testando região da barra de HP...")
    print("Posicione a janela do jogo e pressione ENTER")
    input("Pronto? ")
    
    # Região definida pelo configurador
    hp_bar_region = (9, 7, 497, 7)
    
    print(f"Capturando região: {hp_bar_region}")
    screenshot = pyautogui.screenshot(region=hp_bar_region)
    screenshot.save("../healings/test_current_hp.png")
    print("Imagem salva: ../healings/test_current_hp.png")
    
    # Análise simples
    width, height = screenshot.size
    print(f"Dimensões: {width}x{height} pixels")
    
    last_colored_x = 0
    for x in range(width):
        has_color = False
        for y in range(height):
            r, g, b = screenshot.getpixel((x, y))
            brightness = r + g + b
            if brightness > 80:
                has_color = True
                break
        
        if has_color:
            last_colored_x = x
    
    fill_ratio = (last_colored_x + 1) / width
    estimated_hp = int(1755 * fill_ratio)
    
    print(f"Largura total: {width}px")
    print(f"Preenchido até: {last_colored_x + 1}px")
    print(f"Proporção: {fill_ratio:.1%}")
    print(f"HP estimado: {estimated_hp}/1755")
    
    if estimated_hp > 1755:
        print("PROBLEMA: HP estimado maior que máximo!")
        print("A região pode estar incluindo elementos extras")
    elif estimated_hp == 1755:
        print("HP detectado como CHEIO")
    elif estimated_hp > 1500:
        print("HP detectado como ALTO (sem healing)")
    elif estimated_hp > 1200:
        print("HP detectado como MÉDIO (usar tecla 2)")
    elif estimated_hp > 500:
        print("HP detectado como BAIXO (usar tecla 3)")
    else:
        print("HP detectado como CRÍTICO (usar F1)")

if __name__ == "__main__":
    test_region()