#!/usr/bin/env python3
"""
Teste específico para detectar HP vermelho.
"""

import pyautogui
import time

def test_red_detection():
    """Testa especificamente a detecção de HP vermelho"""
    
    print("=" * 60)
    print("TESTE ESPECÍFICO PARA DETECÇÃO DE HP VERMELHO")
    print("=" * 60)
    print("Deixe o HP do personagem VERMELHO e pressione Enter...")
    input()
    
    def analyze_red_pixels():
        try:
            # Região da barra de HP
            hp_bar_region = (9, 7, 497, 7)
            screenshot = pyautogui.screenshot(region=hp_bar_region)
            width, height = screenshot.size
            
            # Salva debug
            screenshot.save("../debug_red_test.png")
            print(f"[DEBUG] Screenshot salvo como debug_red_test.png ({width}x{height})")
            
            red_candidates = 0
            total_colored = 0
            pixel_samples = []
            
            # Analisa cada pixel
            for x in range(width):
                for y in range(height):
                    r, g, b = screenshot.getpixel((x, y))
                    
                    brightness = r + g + b
                    if brightness < 50:
                        continue
                        
                    total_colored += 1
                    
                    # Coleta amostras de pixels para análise
                    if len(pixel_samples) < 20:
                        pixel_samples.append((x, y, r, g, b))
                    
                    # Testa vários critérios para vermelho
                    is_red_1 = r > 80 and g < 80 and b < 80 and r > g and r > b
                    is_red_2 = r > 60 and g < 60 and b < 60 and r > (g + b)
                    is_red_3 = r > 100 and g < 50 and b < 50
                    is_red_4 = r > g * 1.5 and r > b * 1.5 and r > 70
                    
                    if is_red_1 or is_red_2 or is_red_3 or is_red_4:
                        red_candidates += 1
            
            print(f"\n[ANÁLISE DETALHADA]")
            print(f"Total de pixels coloridos: {total_colored}")
            print(f"Candidatos a vermelho: {red_candidates}")
            
            if red_candidates > 0:
                red_ratio = red_candidates / total_colored if total_colored > 0 else 0
                print(f"Proporção de vermelho: {red_ratio:.2%}")
            
            print(f"\n[AMOSTRA DE PIXELS]")
            for i, (x, y, r, g, b) in enumerate(pixel_samples):
                is_red_1 = r > 80 and g < 80 and b < 80 and r > g and r > b
                is_red_2 = r > 60 and g < 60 and b < 60 and r > (g + b)
                is_red_3 = r > 100 and g < 50 and b < 50
                is_red_4 = r > g * 1.5 and r > b * 1.5 and r > 70
                
                status = []
                if is_red_1: status.append("RED1")
                if is_red_2: status.append("RED2") 
                if is_red_3: status.append("RED3")
                if is_red_4: status.append("RED4")
                
                if not status: status.append("NÃO-VERMELHO")
                
                print(f"  Pixel {i+1}: ({x},{y}) RGB({r},{g},{b}) -> {' '.join(status)}")
            
            # Recomendação
            if red_candidates > 0:
                print(f"\n✅ VERMELHO DETECTADO! ({red_candidates} pixels)")
                if red_ratio > 0.05:
                    print("🎯 Sistema deve detectar como HP BAIXO")
                else:
                    print("⚠️  Poucos pixels vermelhos, pode não ser detectado")
            else:
                print(f"\n❌ NENHUM VERMELHO DETECTADO")
                print("💡 Possíveis soluções:")
                print("   - Verificar se HP está realmente vermelho")
                print("   - Ajustar critérios de detecção")
                print("   - Verificar região da captura")
                
        except Exception as e:
            print(f"[ERRO] {e}")
    
    while True:
        print(f"\n--- Teste de Vermelho {time.strftime('%H:%M:%S')} ---")
        analyze_red_pixels()
        
        resp = input("\nTeste novamente? (s/N): ").lower()
        if resp != 's':
            break
    
    print("\n[INFO] Teste concluído")

if __name__ == "__main__":
    test_red_detection()