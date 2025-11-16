#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para definir a região exata da barra de HP
"""

import pyautogui
import time

def get_mouse_coordinates():
    """Captura coordenadas do mouse para definir região"""
    print("=== DEFINIÇÃO DA REGIÃO DA BARRA DE HP ===")
    print("\nInstruções:")
    print("1. Posicione a janela do jogo")
    print("2. Mova o mouse para o INÍCIO da barra de HP (lado esquerdo)")
    print("3. Pressione ENTER")
    
    input("Mouse no INÍCIO da barra de HP e pressione ENTER: ")
    x1, y1 = pyautogui.position()
    print(f"Início: ({x1}, {y1})")
    
    print("\n4. Agora mova o mouse para o FIM da barra de HP (lado direito)")
    print("5. Pressione ENTER")
    
    input("Mouse no FIM da barra de HP e pressione ENTER: ")
    x2, y2 = pyautogui.position()
    print(f"Fim: ({x2}, {y2})")
    
    # Calcula região
    x = min(x1, x2)
    y = min(y1, y2) 
    width = abs(x2 - x1)
    height = abs(y2 - y1)
    
    # Adiciona margem para capturar melhor
    margin = 3
    x -= margin
    y -= margin
    width += margin * 2
    height += margin * 2
    
    region = (x, y, width, height)
    
    print(f"\nRegião calculada: {region}")
    
    # Teste da região
    print("\nTestando a região...")
    screenshot = pyautogui.screenshot(region=region)
    screenshot.save("../healings/hp_region_test.png")
    print("Região salva em: ../healings/hp_region_test.png")
    
    # Análise da região
    width_px, height_px = screenshot.size
    total_pixels = width_px * height_px
    colored_pixels = 0
    green_pixels = 0
    
    for x_px in range(width_px):
        for y_px in range(height_px):
            r, g, b = screenshot.getpixel((x_px, y_px))
            brightness = r + g + b
            
            if brightness > 80:
                colored_pixels += 1
                if g > r and g > b and g > 100:
                    green_pixels += 1
    
    fill_ratio = colored_pixels / total_pixels if total_pixels > 0 else 0
    green_ratio = green_pixels / colored_pixels if colored_pixels > 0 else 0
    
    print(f"\nAnálise da região:")
    print(f"Pixels totais: {total_pixels}")
    print(f"Pixels coloridos: {colored_pixels} ({fill_ratio:.2%})")
    print(f"Pixels verdes: {green_pixels} ({green_ratio:.2%})")
    
    # Estimativa de HP
    estimated_hp = int(1755 * fill_ratio) if fill_ratio > 0.1 else int(1755 * green_ratio)
    print(f"HP estimado: {estimated_hp}/1755")
    
    print(f"\n=== RESULTADO ===")
    print(f"Use esta região no healing.py:")
    print(f"hp_bar_region = {region}")
    
    return region

def test_multiple_regions():
    """Testa várias regiões automaticamente"""
    print("=== TESTE AUTOMÁTICO DE REGIÕES ===")
    print("Posicione a janela do jogo e pressione ENTER")
    input("Pronto? ")
    
    # Regiões para testar baseadas na interface
    regions = [
        ("Região original", (16, 9, 700, 16)),
        ("Barra HP estreita", (175, 9, 180, 8)),
        ("Barra HP média", (150, 8, 220, 12)),
        ("Barra HP ampla", (100, 6, 300, 18)),
        ("Só números HP", (175, 9, 100, 10)),
    ]
    
    best_region = None
    best_score = 0
    
    for name, region in regions:
        print(f"\n--- Testando {name}: {region} ---")
        
        try:
            screenshot = pyautogui.screenshot(region=region)
            filename = f"../healings/test_{name.replace(' ', '_').lower()}.png"
            screenshot.save(filename)
            
            # Análise
            width, height = screenshot.size
            total_pixels = width * height
            colored_pixels = 0
            green_pixels = 0
            
            for x in range(width):
                for y in range(height):
                    r, g, b = screenshot.getpixel((x, y))
                    brightness = r + g + b
                    
                    if brightness > 80:
                        colored_pixels += 1
                        if g > r and g > b and g > 100:
                            green_pixels += 1
            
            fill_ratio = colored_pixels / total_pixels if total_pixels > 0 else 0
            green_ratio = green_pixels / colored_pixels if colored_pixels > 0 else 0
            
            # Score baseado na qualidade da detecção
            score = fill_ratio * green_ratio
            
            print(f"Pixels coloridos: {colored_pixels}/{total_pixels} ({fill_ratio:.2%})")
            print(f"Pixels verdes: {green_pixels} ({green_ratio:.2%})")
            print(f"Score: {score:.3f}")
            print(f"Imagem: {filename}")
            
            if score > best_score:
                best_score = score
                best_region = region
                
        except Exception as e:
            print(f"Erro: {e}")
    
    if best_region:
        print(f"\n=== MELHOR REGIÃO ===")
        print(f"Região: {best_region}")
        print(f"Score: {best_score:.3f}")
        print(f"\nUse esta configuração:")
        print(f"hp_bar_region = {best_region}")

def main():
    """Menu principal"""
    print("=== CONFIGURADOR DE REGIÃO HP ===")
    print("1. Definir região manualmente (recomendado)")
    print("2. Testar regiões automaticamente") 
    print("3. Sair")
    
    choice = input("Escolha (1-3): ").strip()
    
    if choice == "1":
        get_mouse_coordinates()
    elif choice == "2":
        test_multiple_regions()
    elif choice == "3":
        print("Saindo...")
    else:
        print("Opção inválida")

if __name__ == "__main__":
    main()