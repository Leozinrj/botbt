#!/usr/bin/env python3
"""
Teste do sistema de detecção de HP por cores.
"""

import pyautogui
import time

def test_color_detection():
    """Testa a detecção de cores do HP"""
    
    print("=" * 50)
    print("TESTE DE DETECÇÃO DE CORES DO HP")
    print("=" * 50)
    print("Posicione o jogo e pressione Enter para começar...")
    input()
    
    def detect_hp_colors():
        """Função de detecção baseada no código principal"""
        try:
            # Região da barra de HP
            hp_bar_region = (9, 7, 497, 7)
            
            screenshot = pyautogui.screenshot(region=hp_bar_region)
            width, height = screenshot.size
            
            # Salva screenshot para debug
            screenshot.save("../debug_hp_colors.png")
            print(f"[DEBUG] Screenshot salvo como debug_hp_colors.png ({width}x{height})")
            
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
                    
                    # Ignora pixels muito escuros (fundo)
                    brightness = r + g + b
                    if brightness < 80:
                        continue
                        
                    total_colored += 1
                    
                    # Classificação das cores
                    if g > 120 and r < 100 and b < 100:
                        # Verde escuro - HP cheio
                        dark_green_pixels += 1
                    elif g > 100 and r > 80 and r < 120 and b < 80:
                        # Verde musgo/claro - HP 80%
                        light_green_pixels += 1
                    elif r > 120 and g > 100 and b < 80:
                        # Amarelo - HP médio
                        yellow_pixels += 1
                    elif r > 120 and g < 100 and b < 80:
                        # Vermelho - HP baixo
                        red_pixels += 1
            
            if total_colored == 0:
                print("[ERRO] Nenhum pixel colorido encontrado na barra de HP")
                return "unknown"
            
            # Calcula proporções
            total = dark_green_pixels + light_green_pixels + yellow_pixels + red_pixels
            if total == 0:
                print("[ERRO] Nenhuma cor válida detectada")
                return "unknown"
                
            dark_green_ratio = dark_green_pixels / total
            light_green_ratio = light_green_pixels / total  
            yellow_ratio = yellow_pixels / total
            red_ratio = red_pixels / total
            
            print(f"\n[RESULTADOS] Análise de cores:")
            print(f"  Total de pixels coloridos: {total_colored}")
            print(f"  Pixels classificados: {total}")
            print(f"  Verde escuro: {dark_green_pixels} pixels ({dark_green_ratio:.2%})")
            print(f"  Verde musgo: {light_green_pixels} pixels ({light_green_ratio:.2%})")
            print(f"  Amarelo: {yellow_pixels} pixels ({yellow_ratio:.2%})")
            print(f"  Vermelho: {red_pixels} pixels ({red_ratio:.2%})")
            
            # Determina estado do HP baseado na cor predominante
            if dark_green_ratio > 0.5:
                return "full"  # HP cheio - verde escuro
            elif light_green_ratio > 0.3:
                return "80p"   # HP 80% - verde musgo
            elif yellow_ratio > 0.3:
                return "medium" # HP médio - amarelo
            elif red_ratio > 0.2:
                return "low"    # HP baixo - vermelho
            else:
                return "unknown"
                
        except Exception as e:
            print(f"[ERRO] Detecção de cores: {e}")
            return "unknown"
    
    # Testa detecção em loop
    try:
        while True:
            print(f"\n--- Teste {time.strftime('%H:%M:%S')} ---")
            
            hp_state = detect_hp_colors()
            
            state_messages = {
                "full": "🟢 HP CHEIO (Verde escuro) - SEM HEALING",
                "80p": "🟡 HP 80% (Verde musgo) - TECLA 2",
                "medium": "🟠 HP MÉDIO (Amarelo) - TECLA 3",
                "low": "🔴 HP BAIXO (Vermelho) - F1 + TECLA 3",
                "unknown": "❓ ESTADO DESCONHECIDO"
            }
            
            print(f"\n[RESULTADO FINAL] {state_messages.get(hp_state, hp_state)}")
            
            print("\nPressione Enter para testar novamente ou Ctrl+C para sair...")
            input()
            
    except KeyboardInterrupt:
        print("\n[INFO] Teste interrompido pelo usuário")
    except Exception as e:
        print(f"[ERRO] Teste: {e}")

if __name__ == "__main__":
    test_color_detection()