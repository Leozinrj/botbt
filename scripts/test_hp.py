#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de teste para verificar a detecção de HP
"""

import pyautogui
import time

def test_hp_detection():
    """Teste simples para verificar a detecção de HP"""
    print("=== TESTE DE DETECÇÃO DE HP ===")
    print("Posicione a janela do jogo e pressione ENTER")
    input("Pronto? ")
    
    # Coordenadas da barra de HP baseadas na sua tela
    hp_bar_region = (16, 9, 700, 16)
    
    print(f"Analisando região: {hp_bar_region}")
    
    # Captura a região
    screenshot = pyautogui.screenshot(region=hp_bar_region)
    
    # Salva para análise
    screenshot.save("../healings/hp_test_capture.png")
    print("Captura salva em: ../healings/hp_test_capture.png")
    
    # Análise de cores
    width, height = screenshot.size
    total_pixels = width * height
    
    green_pixels = 0
    yellow_pixels = 0  
    red_pixels = 0
    colored_pixels = 0
    
    print(f"Analisando {total_pixels} pixels...")
    
    for x in range(width):
        for y in range(height):
            r, g, b = screenshot.getpixel((x, y))
            
            # Ignora pixels muito escuros
            if r + g + b < 80:
                continue
                
            colored_pixels += 1
            
            # Critérios mais flexíveis para detecção de cores
            brightness = r + g + b
            
            # Verde (HP alto/médio-alto) - mais flexível
            if g >= r and g >= b and g > 80:
                green_pixels += 1
            # Amarelo/laranja (HP médio)
            elif r > 80 and g > 60 and b < 100 and abs(r - g) < 50:
                yellow_pixels += 1  
            # Vermelho (HP baixo)
            elif r > 100 and r > g + 20 and r > b + 20:
                red_pixels += 1
    
    print(f"\nRESULTADOS:")
    print(f"Pixels totais: {total_pixels}")
    print(f"Pixels coloridos: {colored_pixels}")
    print(f"Verde (HP alto): {green_pixels} ({green_pixels/total_pixels*100:.1f}%)")
    print(f"Amarelo (HP médio): {yellow_pixels} ({yellow_pixels/total_pixels*100:.1f}%)")
    print(f"Vermelho (HP baixo): {red_pixels} ({red_pixels/total_pixels*100:.1f}%)")
    
    # Estimativa de HP
    if colored_pixels > 0:
        green_ratio = green_pixels / colored_pixels
        yellow_ratio = yellow_pixels / colored_pixels
        red_ratio = red_pixels / colored_pixels
        
        print(f"\nRATIOS na barra:")
        print(f"Verde: {green_ratio:.3f}")
        print(f"Amarelo: {yellow_ratio:.3f}") 
        print(f"Vermelho: {red_ratio:.3f}")
        
        if green_ratio > 0.7:
            hp_estimate = 90 + (green_ratio - 0.7) * 33
        elif green_ratio > 0.3:
            hp_estimate = 60 + green_ratio * 40
        elif yellow_ratio > 0.3:
            hp_estimate = 30 + yellow_ratio * 50
        elif red_ratio > 0.1:
            hp_estimate = 10 + red_ratio * 30
        else:
            hp_estimate = 5
            
        print(f"\nHP ESTIMADO: {hp_estimate:.0f}%")
    else:
        print("\nNÃO DETECTOU BARRA DE HP")

if __name__ == "__main__":
    test_hp_detection()