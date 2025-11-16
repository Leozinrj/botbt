#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script auxiliar para capturar imagens de referência da barra de HP
Use este script para criar os templates necessários para o sistema de healing.
"""

import pyautogui
import time
import os

def capture_hp_template(hp_level_name, description):
    """Captura uma imagem da barra de HP para usar como template"""
    print(f"\n=== Captura: {hp_level_name} ===")
    print(f"Descrição: {description}")
    print("\nInstruções:")
    print("1. Deixe seu personagem com o HP no nível desejado")
    print("2. Posicione a barra de HP bem visível na tela")
    print("3. Pressione ENTER quando estiver pronto")
    print("4. Você terá 3 segundos para posicionar o cursor")
    print("5. Clique e arraste para selecionar APENAS a barra de HP")
    
    input("Pressione ENTER para começar...")
    
    print("Preparando em 3...")
    time.sleep(1)
    print("2...")
    time.sleep(1)
    print("1...")
    time.sleep(1)
    print("Selecione a barra de HP agora!")
    
    try:
        # Aguarda o usuário selecionar a região
        region = pyautogui.screenshot()
        filename = f"../healings/hp_{hp_level_name}.png"
        
        # Cria o diretório se não existir
        os.makedirs("../healings", exist_ok=True)
        
        # Manual selection - usuário deve usar ferramenta de screenshot
        print(f"\nSalve manualmente a região selecionada como: {filename}")
        print("Ou use este script como referência para coordenadas específicas")
        
        return True
        
    except Exception as e:
        print(f"Erro na captura: {e}")
        return False

def main():
    """Script principal para capturar todos os templates de HP"""
    print("=" * 60)
    print("CAPTURADOR DE TEMPLATES DE HP")
    print("=" * 60)
    
    print("\nEste script irá te ajudar a capturar imagens da barra de HP")
    print("em diferentes níveis para usar no sistema de healing automático.")
    
    templates = [
        ("emergency", "HP crítico (10-15%) - cor vermelha escura"),
        ("critical", "HP baixo (25-30%) - cor vermelha normal"),
        ("low", "HP médio (45-50%) - cor vermelha clara"),
        ("medium", "HP médio-alto (65-70%) - mistura vermelho/verde"),
        ("high", "HP alto (85-90%) - cor verde clara"),
        ("full", "HP cheio (100%) - cor verde completa")
    ]
    
    print("\nVamos capturar os seguintes templates:")
    for name, desc in templates:
        print(f"- {name}: {desc}")
    
    print("\nDICA IMPORTANTE:")
    print("- Capture apenas a BARRA DE HP, não a interface toda")
    print("- Certifique-se de que a barra está bem visível")
    print("- Mantenha sempre a mesma resolução e zoom")
    print("- Use Print Screen + Paint para recortar e salvar as imagens")
    
    for template_name, description in templates:
        try:
            if capture_hp_template(template_name, description):
                print(f"✓ Template {template_name} preparado")
            else:
                print(f"✗ Erro no template {template_name}")
        except KeyboardInterrupt:
            print("\nCaptura cancelada pelo usuário")
            break
        except Exception as e:
            print(f"Erro: {e}")
    
    print("\n=== INSTRUÇÕES FINAIS ===")
    print("1. Use Print Screen para capturar a tela inteira")
    print("2. Cole no Paint e recorte apenas a barra de HP")
    print("3. Salve as imagens na pasta 'healings/' com os nomes:")
    print("   - hp_emergency.png (HP ~10%)")
    print("   - hp_critical.png (HP ~25%)")
    print("   - hp_low.png (HP ~45%)")
    print("   - hp_medium.png (HP ~65%)")
    print("   - hp_high.png (HP ~85%)")
    print("   - hp_full.png (HP ~100%)")
    
    print("\n4. Alternativamente, você pode editar o script healing.py")
    print("   e configurar coordenadas específicas da barra de HP")
    print("   na função get_hp_percentage() linha ~90")

if __name__ == "__main__":
    main()